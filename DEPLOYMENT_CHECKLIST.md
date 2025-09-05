# Coolify Deployment Checklist

## Pre-Deployment Checklist

### ✅ Repository Setup
- [ ] Code is pushed to a Git repository (GitHub, GitLab, etc.)
- [ ] Repository is accessible from your Coolify instance
- [ ] All necessary files are included (Dockerfile, requirements.txt, etc.)

### ✅ Configuration Preparation
- [ ] AI Power Grid API key is ready
- [ ] OpenAI API key (if using OpenAI-compatible endpoints)
- [ ] KoboldAI server URL (if using KoboldAI)
- [ ] Model configuration details

### ✅ Coolify Setup
- [ ] Coolify instance is running and accessible
- [ ] You have admin access to Coolify dashboard
- [ ] Docker registry access (if using Docker image deployment)

## Deployment Steps

### 1. Create New Application in Coolify
- [ ] Go to Coolify dashboard
- [ ] Click "New Resource" → "Application"
- [ ] Choose deployment method:
  - [ ] Git Repository (recommended)
  - [ ] Docker Image

### 2. Configure Application
- [ ] Set application name (e.g., "ai-power-grid-bridge")
- [ ] Choose build pack: "Docker"
- [ ] Set port to 0 (no HTTP endpoints)
- [ ] Configure resource limits:
  - [ ] CPU: 0.5-2 cores
  - [ ] Memory: 512MB-2GB
  - [ ] Storage: 1GB

### 3. Environment Variables
- [ ] Add required variables:
  - [ ] `API_KEY` = your_ai_power_grid_api_key
- [ ] Add optional variables:
  - [ ] `HORDE_URL` = https://api.aipowergrid.io/
  - [ ] `QUEUE_SIZE` = 0
- [ ] Add endpoint-specific variables:
  - [ ] For OpenAI: `OPENAI_API_KEY`, `OPENAI_URL`, `OPENAI_MODEL`
  - [ ] For KoboldAI: `KAI_URL`

### 4. Deploy
- [ ] Review configuration
- [ ] Click "Deploy" or "Save"
- [ ] Monitor deployment progress
- [ ] Check for any build errors

## Post-Deployment Verification

### ✅ Application Status
- [ ] Application shows as "Running" in Coolify
- [ ] No error messages in deployment logs
- [ ] Health checks are passing

### ✅ Logs Verification
- [ ] Check application logs in Coolify
- [ ] Look for successful worker startup messages
- [ ] Verify no configuration errors
- [ ] Check for successful API connections

### ✅ Functionality Test
- [ ] Verify workers appear in AI Power Grid dashboard
- [ ] Test with a simple request (if possible)
- [ ] Monitor resource usage
- [ ] Check for any error messages

## Troubleshooting

### Common Issues and Solutions

#### Build Failures
- [ ] Check Dockerfile syntax
- [ ] Verify all dependencies in requirements.txt
- [ ] Ensure repository is accessible

#### Configuration Errors
- [ ] Verify all required environment variables are set
- [ ] Check API key format and permissions
- [ ] Validate endpoint URLs

#### Runtime Errors
- [ ] Check application logs for specific error messages
- [ ] Verify network connectivity to external APIs
- [ ] Monitor resource usage (CPU/memory)

#### Health Check Failures
- [ ] Verify AI Power Grid API is accessible
- [ ] Check network firewall rules
- [ ] Ensure API key is valid

## Monitoring

### Regular Checks
- [ ] Monitor application status in Coolify dashboard
- [ ] Check resource usage (CPU, memory, storage)
- [ ] Review application logs for errors
- [ ] Verify workers are active in AI Power Grid

### Maintenance
- [ ] Update application when new versions are available
- [ ] Rotate API keys periodically
- [ ] Monitor for security updates
- [ ] Backup configuration if needed

## Support Resources

- [AI Power Grid Documentation](https://docs.aipowergrid.io/)
- [Coolify Documentation](https://coolify.io/docs)
- [Application Logs in Coolify Dashboard]
- [AI Power Grid Worker Dashboard]
