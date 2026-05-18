# IAM tightening for `openinnova-deploy`

During the initial setup, the `openinnova-deploy` IAM user collected five
AWS-managed `*FullAccess` policies (S3, CloudFront, Route 53, ACM, CloudWatch
Logs). Those permissions are far broader than what a deploy script needs.

Once the infrastructure is in place, the deploy user only needs to:

- read/write objects in the `openinnova-website` S3 bucket
- create cache invalidations on the CloudFront distribution `E2IUEDFNFT7LLX`

The custom policy in [iam-policy-deploy.json](iam-policy-deploy.json) grants
exactly that and nothing else.

## Apply it

Console steps (the deploy user does not have IAM permissions to do this from
the CLI — needs an admin):

1. **IAM → Policies → Create policy → JSON tab**.
2. Paste the contents of [iam-policy-deploy.json](iam-policy-deploy.json).
3. **Next**.
4. Name: `openinnova-deploy-minimal`. Description: "Least-privilege deploy
   permissions for openinnova-website".
5. **Create policy**.

Then attach it to the user and remove the broad ones:

6. **IAM → Users → openinnova-deploy → Permissions**.
7. **Add permissions → Attach policies directly** → search
   `openinnova-deploy-minimal` → attach.
8. Detach (one by one) the temporary policies:
   - `AmazonS3FullAccess`
   - `CloudFrontFullAccess`
   - `AmazonRoute53FullAccess`
   - `AWSCertificateManagerFullAccess`
   - `CloudWatchLogsFullAccess`

After this, `openinnova-deploy` can run `./scripts/deploy.sh` (deploy + cache
invalidation) and nothing else.

## When to widen again

If you need to change AWS infra (new distribution settings, certificate
renewal that fails auto-renew, new DNS records, new IAM users, etc.):

- Either re-attach the relevant `*FullAccess` policy temporarily, do the
  change, then detach.
- Or do the change in the AWS console with an admin user.

The CloudFront distribution ID is hardcoded in the policy. If you ever
replace the distribution, update the policy `Resource` ARN as well.

## Verify the tightening worked

After applying the new policy, the deploy still works:

```bash
AWS_PROFILE=open-innova ./scripts/deploy.sh
```

The user can no longer:

- list other S3 buckets, create or modify buckets
- modify the CloudFront distribution config
- touch DNS, certificates, or logs delivery

Try, as a sanity check:

```bash
AWS_PROFILE=open-innova aws s3 ls           # expects AccessDenied (no ListAllMyBuckets)
AWS_PROFILE=open-innova aws route53 list-hosted-zones   # expects AccessDenied
```

Both should fail. The deploy script should still succeed.
