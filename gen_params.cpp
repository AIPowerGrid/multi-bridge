def transform_genparams(genparams, api_format):
    global chatcompl_adapter, maxctx
    #api format 1=basic,2=kai,3=oai,4=oai-chat,5=interrogate,6=ollama,7=ollamachat
    #alias all nonstandard alternative names for rep pen.
    rp1 = float(genparams.get('repeat_penalty', 1.0))
    rp2 = float(genparams.get('repetition_penalty', 1.0))
    rp3 = float(genparams.get('rep_pen', 1.0))
    rp_max = max(rp1,rp2,rp3)
    genparams["rep_pen"] = rp_max
    if "use_default_badwordsids" in genparams and "ban_eos_token" not in genparams:
        genparams["ban_eos_token"] = genparams.get('use_default_badwordsids', False)

    if api_format==1:
        genparams["prompt"] = genparams.get('text', "")
        genparams["top_k"] = int(genparams.get('top_k', 120))
        genparams["max_length"] = int(genparams.get('max', 200))

    elif api_format==2:
        pass

    elif api_format==3 or api_format==4 or api_format==7:
        default_adapter = {} if chatcompl_adapter is None else chatcompl_adapter
        adapter_obj = genparams.get('adapter', default_adapter)
        default_max_tok = (adapter_obj.get("max_length", 512) if (api_format==4 or api_format==7) else 200)
        genparams["max_length"] = int(genparams.get('max_tokens', genparams.get('max_completion_tokens', default_max_tok)))
        presence_penalty = genparams.get('presence_penalty', genparams.get('frequency_penalty', 0.0))
        genparams["presence_penalty"] = float(presence_penalty)
        # openai allows either a string or a list as a stop sequence
        if isinstance(genparams.get('stop',[]), list):
            genparams["stop_sequence"] = genparams.get('stop', [])
        else:
            genparams["stop_sequence"] = [genparams.get('stop')]

        genparams["sampler_seed"] = tryparseint(genparams.get('seed', -1))
        genparams["mirostat"] = genparams.get('mirostat_mode', 0)

        if api_format==4 or api_format==7: #handle ollama chat here too
            # translate openai chat completion messages format into one big string.
            messages_array = genparams.get('messages', [])
            messages_string = ""
            system_message_start = adapter_obj.get("system_start", "\n### Instruction:\n")
            system_message_end = adapter_obj.get("system_end", "")
            user_message_start = adapter_obj.get("user_start", "\n### Instruction:\n")
            user_message_end = adapter_obj.get("user_end", "")
            assistant_message_start = adapter_obj.get("assistant_start", "\n### Response:\n")
            assistant_message_end = adapter_obj.get("assistant_end", "")
            tools_message_start = adapter_obj.get("tools_start", "")
            tools_message_end = adapter_obj.get("tools_end", "")
            images_added = []

            message_index = 0
            for message in messages_array:
                message_index += 1
                if message['role'] == "system":
                    messages_string += system_message_start
                elif message['role'] == "user":
                    messages_string += user_message_start
                elif message['role'] == "assistant":
                    messages_string += assistant_message_start
                elif message['role'] == "tool":
                    messages_string += tools_message_start

                # content can be a string or an array of objects
                curr_content = message.get("content",None)
                if not curr_content:
                    pass  # do nothing
                elif isinstance(curr_content, str):
                    messages_string += curr_content
                elif isinstance(curr_content, list): #is an array
                    for item in curr_content:
                        if item['type']=="text":
                                messages_string += item['text']
                        elif item['type']=="image_url":
                            if item['image_url'] and item['image_url']['url'] and item['image_url']['url'].startswith("data:image"):
                                images_added.append(item['image_url']['url'].split(",", 1)[1])
                # If last message, add any tools calls after message content and before message end token if any
                if message['role'] == "user" and message_index == len(messages_array):
                    # Check if user is passing a openai tools array, if so add to end of prompt before assistant prompt unless tool_choice has been set to None
                    tools_array = genparams.get('tools', [])
                    if tools_array and len(tools_array) > 0 and genparams.get('tool_choice',None) is not None:
                        response_array = [{"id": "insert an id for the response", "type": "function", "function": {"name": "insert the name of the function you want to call", "arguments": {"first property key": "first property value", "second property key": "second property value"}}}]
                        json_formatting_instruction = " Use this style of JSON object formatting to give your answer if you think the user is asking you to perform an action: " + json.dumps(response_array, indent=0)
                        tools_string = json.dumps(tools_array, indent=0)
                        messages_string += tools_string
                        specified_function = None
                        if isinstance(genparams.get('tool_choice'), dict):
                             try:
                                specified_function = genparams.get('tool_choice').get('function').get('name')
                                json_formatting_instruction = f"The user is asking you to use the style of this JSON object formatting to complete the parameters for the specific function named {specified_function} in the following format: " + json.dumps([{"id": "insert an id for the response", "type": "function", "function": {"name": f"{specified_function}", "arguments": {"first property key": "first property value", "second property key": "second property value"}}}], indent=0)
                             except Exception:
                                # In case of any issues, just revert back to no specified function
                                pass
                        messages_string += json_formatting_instruction

                        # Set temperature low automatically if function calling
                        genparams["temperature"] = 0.2
                        genparams["using_openai_tools"] = True

                        # Set grammar to llamacpp example grammar to force json response (see https://github.com/ggerganov/llama.cpp/blob/master/grammars/json_arr.gbnf)
                        genparams["grammar"] = r"""
root   ::= arr
value  ::= object | array | string | number | ("true" | "false" | "null") ws
arr  ::=
  "[\n" ws (
            value
    (",\n" ws value)*
  )? "]"
object ::=
  "{" ws (
            string ":" ws value
    ("," ws string ":" ws value)*
  )? "}" ws
array  ::=
  "[" ws (
            value
    ("," ws value)*
  )? "]" ws
string ::=
  "\"" (
    [^"\\\x7F\x00-\x1F] |
    "\\" (["\\bfnrt] | "u" [0-9a-fA-F]{4})
  )* "\"" ws
number ::= ("-"? ([0-9] | [1-9] [0-9]{0,15})) ("." [0-9]+)? ([eE] [-+]? [1-9] [0-9]{0,15})? ws
ws ::= | " " | "\n" [ \t]{0,20}
"""
                if message['role'] == "system":
                    messages_string += system_message_end
                elif message['role'] == "user":
                    messages_string += user_message_end
                elif message['role'] == "assistant":
                    messages_string += assistant_message_end
                elif message['role'] == "tool":
                    messages_string += tools_message_end

            messages_string += assistant_message_start
            genparams["prompt"] = messages_string
            if len(images_added)>0:
                genparams["images"] = images_added
            if len(genparams.get('stop_sequence', []))==0: #only set stop seq if it wont overwrite existing
                genparams["stop_sequence"] = [user_message_start.strip(),assistant_message_start.strip()]
            else:
                genparams["stop_sequence"].append(user_message_start.strip())
                genparams["stop_sequence"].append(assistant_message_start.strip())
            genparams["trim_stop"] = True


    elif api_format==5:
        firstimg = genparams.get('image', "")
        genparams["images"] = [firstimg]
        genparams["max_length"] = 42
        adapter_obj = {} if chatcompl_adapter is None else chatcompl_adapter
        user_message_start = adapter_obj.get("user_start", "### Instruction:")
        assistant_message_start = adapter_obj.get("assistant_start", "### Response:")
        genparams["prompt"] = f"{user_message_start} In one sentence, write a descriptive caption for this image.\n{assistant_message_start}"

    elif api_format==6:
        detokstr = ""
        tokids = genparams.get('context', [])
        adapter_obj = {} if chatcompl_adapter is None else chatcompl_adapter
        user_message_start = adapter_obj.get("user_start", "\n\n### Instruction:\n")
        assistant_message_start = adapter_obj.get("assistant_start", "\n\n### Response:\n")
        try:
            detokstr = detokenize_ids(tokids)
        except Exception as e:
            utfprint("Ollama Context Error: " + str(e))
        ollamasysprompt = genparams.get('system', "")
        ollamabodyprompt = f"{detokstr}{user_message_start}{genparams.get('prompt', '')}{assistant_message_start}"
        ollamaopts = genparams.get('options', {})
        genparams["stop_sequence"] = genparams.get('stop', [])
        if "num_predict" in ollamaopts:
            genparams["max_length"] = ollamaopts.get('num_predict', 200)
        if "num_ctx" in ollamaopts:
            genparams["max_context_length"] = ollamaopts.get('num_ctx', maxctx)
        if "temperature" in ollamaopts:
            genparams["temperature"] = ollamaopts.get('temperature', 0.75)
        if "top_k" in ollamaopts:
            genparams["top_k"] = ollamaopts.get('top_k', 100)
        if "top_p" in ollamaopts:
            genparams["top_p"] = ollamaopts.get('top_p', 0.92)
        if "seed" in ollamaopts:
            genparams["sampler_seed"] = tryparseint(ollamaopts.get('seed', -1))
        if "stop" in ollamaopts:
            genparams["stop_sequence"] = ollamaopts.get('stop', [])
        genparams["stop_sequence"].append(user_message_start.strip())
        genparams["stop_sequence"].append(assistant_message_start.strip())
        genparams["trim_stop"] = True
        genparams["ollamasysprompt"] = ollamasysprompt
        genparams["ollamabodyprompt"] = ollamabodyprompt
        genparams["prompt"] = ollamasysprompt + ollamabodyprompt
    return genparams
