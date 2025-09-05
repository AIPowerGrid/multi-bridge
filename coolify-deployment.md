# Coolify Deployment Guide for AI Power Grid Bridge

This guide will help you deploy the AI Power Grid Bridge to Coolify.

## Prerequisites

1. A Coolify instance running
2. AI Power Grid API key
3. Configuration for your AI endpoints (OpenAI-compatible or KoboldAI)

## Step 1: Prepare Your Configuration

### Option A: Environment Variables (Recommended)

Create your configuration using environment variables in Coolify:

```bash
# Required
API_KEY=your_ai_power_grid_api_key_here

# Optional (defaults shown)
HORDE_URL=https://api.aipowergrid.io/
QUEUE_SIZE=0

# OpenAI Endpoint Configuration (if using OpenAI-compatible APIs)
OPENAI_API_KEY=your_openai_api_key
OPENAI_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo

# KoboldAI Endpoint Configuration (if using KoboldAI)
KAI_URL=http://your-koboldai-server:5000
```

### Option B: Configuration File

If you prefer using a configuration file, you can mount it as a volume or create it during deployment.

## Step 2: Deploy to Coolify

### Method 1: Git Repository Deployment

1. **Push your code to a Git repository** (GitHub, GitLab, etc.)
2. **In Coolify dashboard:**
   - Click "New Resource" → "Application"
   - Select "Git Repository"
   - Choose your repository
   - Set build pack to "Docker"
   - Configure environment variables (see Step 1)

### Method 2: Docker Image Deployment

1. **Build and push your Docker image:**
   ```bash
   docker build -t your-registry/ai-power-grid-bridge:latest .
   docker push your-registry/ai-power-grid-bridge:latest
   ```

2. **In Coolify dashboard:**
   - Click "New Resource" → "Application"
   - Select "Docker Image"
   - Enter your image URL: `your-registry/ai-power-grid-bridge:latest`
   - Configure environment variables

## Step 3: Environment Variables Configuration

In Coolify, add these environment variables:

### Required Variables:
- `API_KEY`: Your AI Power Grid API key

### Optional Variables:
- `HORDE_URL`: AI Power Grid API endpoint (default: https://api.aipowergrid.io/)
- `QUEUE_SIZE`: Request queue size (default: 0)

### For OpenAI-compatible endpoints:
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_URL`: OpenAI-compatible API URL
- `OPENAI_MODEL`: Model name to use

### For KoboldAI endpoints:
- `KAI_URL`: KoboldAI server URL

## Step 4: Application Settings

### Port Configuration:
- **No ports needed** - This is a worker service that doesn't expose HTTP endpoints
- Set port to 0 or leave empty in Coolify

### Health Check:
- The Dockerfile includes a health check that pings the AI Power Grid API
- Coolify will use this to monitor the service

### Resource Limits:
- **CPU**: 0.5-2 cores (depending on your workload)
- **Memory**: 512MB-2GB (depending on model size and concurrent requests)
- **Storage**: 1GB should be sufficient

## Step 5: Monitoring and Logs

### Viewing Logs:
- Use Coolify's built-in log viewer
- The application uses loguru for structured logging
- Logs will show worker status, API calls, and errors

### Monitoring:
- Monitor CPU and memory usage
- Check worker status in AI Power Grid dashboard
- Watch for connection errors or API failures

## Troubleshooting

### Common Issues:

1. **API Key Issues:**
   - Verify your AI Power Grid API key is correct
   - Check if the key has proper permissions

2. **Network Connectivity:**
   - Ensure the container can reach external APIs
   - Check firewall rules if using self-hosted Coolify

3. **Configuration Errors:**
   - Verify all required environment variables are set
   - Check the application logs for configuration errors

4. **Resource Issues:**
   - Increase CPU/memory limits if workers are failing
   - Monitor resource usage in Coolify dashboard

### Debug Commands:

```bash
# Check if the container is running
docker ps | grep ai-power-grid-bridge

# View container logs
docker logs ai-power-grid-bridge

# Execute commands in the container
docker exec -it ai-power-grid-bridge /bin/bash
```

## Security Considerations

1. **API Keys**: Never commit API keys to your repository
2. **Network Security**: Use HTTPS for all external API calls
3. **Container Security**: The Dockerfile runs as a non-root user
4. **Secrets Management**: Use Coolify's secrets management for sensitive data

## Scaling

- **Horizontal Scaling**: Deploy multiple instances for higher throughput
- **Vertical Scaling**: Increase CPU/memory limits for larger models
- **Load Balancing**: Not needed as this is a worker service

## Updates

To update your deployment:

1. **Git Repository**: Push changes to your repository, Coolify will auto-deploy
2. **Docker Image**: Build and push a new image, then update in Coolify
3. **Configuration**: Update environment variables in Coolify dashboard

## Support

- Check the [AI Power Grid documentation](https://docs.aipowergrid.io/)
- Review application logs for specific error messages
- Ensure your AI endpoints are properly configured and accessible
