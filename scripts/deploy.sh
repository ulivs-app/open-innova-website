#!/bin/bash

# Open Innova Website Deployment Script
# Builds the site with Hugo and deploys to AWS S3
# Usage: ./scripts/deploy.sh [staging|production]
# Default: staging (safer for testing)

set -e  # Exit on error

# Configuration
BUCKET_NAME="${S3_BUCKET_NAME:-openinnova-website}"
BUCKET_REGION="${S3_BUCKET_REGION:-eu-south-1}"
ENVIRONMENT="${1:-production}"
CF_DISTRIBUTION_ID="${CF_DISTRIBUTION_ID:-E2IUEDFNFT7LLX}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
  echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
  log_info "Checking prerequisites..."

  # Check if Hugo is installed
  if ! command -v hugo &> /dev/null; then
    log_error "Hugo is not installed. Install from https://gohugo.io/"
    exit 1
  fi

  # Check if AWS CLI is installed
  if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Install from https://aws.amazon.com/cli/"
    exit 1
  fi

  # Check if we have AWS credentials
  if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not found. Set up with: aws configure sso"
    exit 1
  fi

  log_info "Prerequisites OK"
}

# Build the site
build_site() {
  log_info "Building site with Hugo..."

  if hugo; then
    log_info "Build successful"
  else
    log_error "Build failed. Check Hugo errors above."
    exit 1
  fi

  # Check that public/ exists and has content
  if [ ! -d "public" ] || [ -z "$(ls -A public)" ]; then
    log_error "Build produced empty public/ directory"
    exit 1
  fi

  log_info "Site built: $(find public -type f | wc -l) files"
}

# Security checks
security_check() {
  log_warn "Running security checks..."

  # Check for AWS credentials in generated files
  if grep -r "AKIA\|aws_secret" public/ 2>/dev/null; then
    log_error "Found AWS credentials in public/ directory! DO NOT DEPLOY!"
    exit 1
  fi

  # Check for sensitive data patterns
  if grep -r "private_key\|password" public/ 2>/dev/null; then
    log_warn "Found potential sensitive data in public/. Review before deploying."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 1
    fi
  fi

  log_info "Security checks passed"
}

# Deploy to S3
deploy_to_s3() {
  log_info "Deploying to S3 bucket: $BUCKET_NAME"

  # First sync: all files with long cache for assets
  log_info "Syncing files with cache control (1 year for assets)..."
  aws s3 sync public/ "s3://$BUCKET_NAME/" \
    --delete \
    --cache-control "public, max-age=31536000, immutable" \
    --exclude "*.html" \
    --exclude "*.xml" \
    --exclude "robots.txt" \
    --exclude "llms.txt" \
    || {
      log_error "S3 sync failed"
      exit 1
    }

  # Second sync: HTML, robots, llms, sitemap with must-revalidate
  log_info "Syncing HTML / sitemap / robots / llms with cache revalidation..."
  aws s3 cp public/ "s3://$BUCKET_NAME/" \
    --recursive \
    --exclude "*" \
    --include "*.html" \
    --include "*.xml" \
    --include "robots.txt" \
    --include "llms.txt" \
    --cache-control "public, max-age=0, must-revalidate" \
    --metadata-directive REPLACE \
    || {
      log_error "HTML sync failed"
      exit 1
    }

  log_info "Deployment to S3 complete"
}

# Invalidate CloudFront cache (optional)
invalidate_cloudfront() {
  if [ -z "$CF_DISTRIBUTION_ID" ]; then
    log_warn "CF_DISTRIBUTION_ID not set. Skipping CloudFront invalidation."
    log_warn "To invalidate: aws cloudfront create-invalidation --distribution-id=YOUR_ID --paths='/*'"
    return
  fi

  log_info "Invalidating CloudFront distribution: $CF_DISTRIBUTION_ID"

  INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$CF_DISTRIBUTION_ID" \
    --paths "/*" \
    --query 'Invalidation.Id' \
    --output text)

  log_info "Invalidation created: $INVALIDATION_ID"
  log_info "This may take 5-10 minutes to complete"
}

# Main flow
main() {
  echo "Open Innova Website Deployment"
  echo "=============================="
  echo "Environment: $ENVIRONMENT"
  echo "Bucket:      $BUCKET_NAME ($BUCKET_REGION)"
  if [ -n "$CF_DISTRIBUTION_ID" ]; then
    echo "CloudFront:  $CF_DISTRIBUTION_ID"
  fi
  echo

  check_prerequisites
  build_site
  security_check

  # Ask for confirmation before deploying
  log_warn "Ready to deploy to S3"
  read -p "Continue with deployment? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_error "Deployment cancelled"
    exit 0
  fi

  deploy_to_s3
  invalidate_cloudfront

  echo
  log_info "Deployment complete."
  echo
  echo "Website is live at:"
  echo "  S3 endpoint:    http://$BUCKET_NAME.s3-website.$BUCKET_REGION.amazonaws.com"
  echo "  Custom domain:  https://openinnova.it"
  echo
}

# Run main
main
