# AWS S3 Deployment Guide

This guide walks you through deploying the Open Innova website to AWS S3 with optional CloudFront for HTTPS and caching.

---

## Architecture

```
Browser → CloudFront (optional) → S3 Bucket (static hosting)
```

The site is generated locally: `hugo` → `public/` → S3.

---

## Step 1: Create the S3 Bucket

```bash
aws s3 mb s3://openinnova-website --region eu-west-1
```

Replace `openinnova-website` with your desired bucket name (must be globally unique).

### Enable Static Website Hosting

```bash
aws s3 website s3://openinnova-website \
  --index-document index.html \
  --error-document 404/index.html
```

This tells S3 to serve `index.html` as the default page and `404/index.html` for missing pages.

---

## Step 2: S3 Bucket Policy

Create a **local file** `bucket-policy.json` (do NOT commit this):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::openinnova-website/*"
    }
  ]
}
```

Apply it:

```bash
aws s3api put-bucket-policy \
  --bucket openinnova-website \
  --policy file://bucket-policy.json
```

This allows anyone to **read** files but NOT write, delete, or list.

---

## Step 3: Block Public Access Settings

Run this command to set correct "Block Public Access" settings:

```bash
aws s3api put-public-access-block \
  --bucket openinnova-website \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false
```

**Explanation:**
- `BlockPublicAcls=true` — Prevent new ACLs from making content public
- `IgnorePublicAcls=true` — Ignore existing ACLs
- `BlockPublicPolicy=false` — Allow our public bucket policy (we wrote it above)
- `RestrictPublicBuckets=false` — Allow public access via our policy

This way: public read (via policy), but no unintended exposure.

---

## Step 4: Credentials — Never in Code

Use **one of these methods** (in order of preference):

### Option A: AWS SSO (Recommended for teams)

```bash
aws configure sso
# Follow the wizard to set up SSO with your organization
export AWS_PROFILE=open-innova-deploy
```

Now `aws s3 sync` will use your SSO credentials automatically.

### Option B: Environment Variables (Recommended for CI/CD)

For GitHub Actions or other CI/CD:

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=eu-west-1
```

**NEVER commit these.** Store in your CI/CD secrets manager (GitHub Actions → Settings → Secrets).

### Option C: Local Credentials File (Local only)

Create `~/.aws/credentials` (NOT committed, local machine only):

```ini
[open-innova-deploy]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```

Then use: `export AWS_PROFILE=open-innova-deploy`

### What NOT to Do

- Never hardcode credentials in scripts or `.env` files
- Never commit AWS keys to git
- Never pass credentials as arguments: `aws s3 sync --access-key=... --secret=...`

---

## Step 5: Deploy

### Full Deploy Command

```bash
# 1. Generate the site
hugo

# 2. Sync to S3 (--delete removes files no longer in public/)
aws s3 sync public/ s3://openinnova-website \
  --delete \
  --cache-control "public, max-age=31536000, immutable"

# 3. Override cache policy for HTML files (they change often)
aws s3 cp public/ s3://openinnova-website/ \
  --recursive \
  --exclude "*" \
  --include "*.html" \
  --cache-control "public, max-age=0, must-revalidate" \
  --metadata-directive REPLACE
```

### What This Does

- **First sync:** Copies all files, sets 1-year cache for static assets (CSS, JS, images)
- **Second sync:** Overwrites HTML files to always revalidate (no cache), so visitors see latest content
- **--delete:** Removes files from S3 that aren't in `public/` anymore

### Automated: Use the Deploy Script

```bash
./scripts/deploy.sh
```

This automates the above. Edit the script if your bucket name is different.

---

## Step 6: CloudFront (Optional but Recommended)

CloudFront adds HTTPS, custom domains, edge caching, and DDoS protection.

### Create Distribution

```bash
aws cloudfront create-distribution \
  --origin-domain-name openinnova-website.s3-website.eu-west-1.amazonaws.com \
  --default-root-object index.html \
  --default-cache-behavior ViewerProtocolPolicy=redirect-to-https
```

Or use the AWS Console for a guided setup.

### After Creating Distribution

Get your Distribution ID:

```bash
aws cloudfront list-distributions --query 'DistributionList.Items[0].Id'
```

### Invalidate Cache After Deploy

After each S3 sync, invalidate CloudFront cache so users see the latest:

```bash
aws cloudfront create-invalidation \
  --distribution-id E1234567890ABC \
  --paths "/*"
```

Add `CF_DISTRIBUTION_ID=...` as an environment variable (never in code).

### Use Custom Domain

1. Buy a domain (e.g., openinnova.it)
2. Request SSL certificate via AWS Certificate Manager
3. Add custom domain to CloudFront distribution
4. Point DNS to CloudFront: `CNAME openinnova.it → d123456.cloudfront.net`

---

## Step 7: Verify Deployment

### Check S3 Sync

Before uploading, do a dry run:

```bash
aws s3 sync public/ s3://openinnova-website \
  --delete \
  --dryrun
```

Review the output to ensure correct files are synced.

### Check Website Is Live

```bash
curl -I https://openinnova-website.s3-website.eu-west-1.amazonaws.com/

# Should return:
# HTTP/1.1 200 OK
# Content-Type: text/html
```

Or if using CloudFront:

```bash
curl -I https://openinnova.it/
```

### Check Robots.txt

```bash
curl https://openinnova.it/robots.txt
```

Should return robots.txt content, allowing GPTBot, ClaudeBot, Google-Extended.

---

## Security Checklist Before Launch

- [ ] AWS credentials are **never** in git history (`git log -S "AKIA"` returns nothing)
- [ ] `npm audit` or `hugo` has no security warnings
- [ ] S3 bucket has **no ACLs** (bucket policy only)
- [ ] MFA Delete is enabled on the bucket (optional, but recommended)
- [ ] CloudTrail logging enabled for audit trail
- [ ] robots.txt is present and allows crawlers
- [ ] llms.txt is present for AI agents
- [ ] HTTPS enforced (CloudFront or S3 HTTPS endpoint)
- [ ] Cache-control headers are correct
- [ ] 404.html exists and is served correctly
- [ ] No sensitive data in `public/` (check before sync)

---

## Rollback

If something goes wrong:

```bash
# List previous versions of your website
aws s3api list-object-versions --bucket openinnova-website

# Restore a specific version
aws s3 cp s3://openinnova-website/index.html index.html --version-id ID_HERE
```

(Requires versioning enabled on the bucket.)

---

## Monitoring & Logs

### CloudWatch Metrics

```bash
aws cloudwatch list-metrics \
  --namespace AWS/S3 \
  --dimensions Name=BucketName,Value=openinnova-website
```

### CloudFront Logs

Enable CloudFront access logs to S3 for analytics.

### S3 Access Logs

Enable S3 access logs to track who is accessing your website.

---

## Troubleshooting

### "Access Denied" When Syncing

- Check AWS credentials are set: `echo $AWS_PROFILE` or `echo $AWS_ACCESS_KEY_ID`
- Verify IAM user has `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` on the bucket
- Run: `aws sts get-caller-identity` to verify you're logged in

### Website Shows 403 Forbidden

- Check bucket policy is set correctly
- Verify "Block Public Access" settings: `BlockPublicPolicy=false`
- Ensure `index.html` exists in bucket root

### Changes Not Visible After Deploy

- Cache issue: Invalidate CloudFront: `aws cloudfront create-invalidation --distribution-id=... --paths="/*"`
- Or wait 1 hour (default cache TTL)
- Check in incognito mode (bypasses browser cache)

---

## Cost Estimate

For a static website like Open Innova:

- **S3 storage:** ~$0.023/GB/month (usually < $1/month)
- **S3 requests:** ~$0.0004 per 1,000 requests (~$0.20/month for 500K requests)
- **CloudFront:** ~$0.085/GB transferred (~$1-10/month for moderate traffic)
- **Total:** ~$2-15/month depending on traffic

Costs scale linearly with traffic; static sites are very cheap to host.

---

## Next Steps

1. Follow steps 1-4 above to set up your bucket
2. Test deploy to staging bucket first: `openinnova-website-staging`
3. Use `./scripts/deploy.sh` for production deploys
4. Monitor with CloudWatch / CloudFront logs
5. Set up alerting for high error rates

---

**Questions?** Check AWS documentation or contact dev@openinnova.it
