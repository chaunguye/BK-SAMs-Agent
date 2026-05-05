# AWS S3 Configuration for BK-SAMs-Agent

To enable file uploads to AWS S3, set the following environment variables in your deployment environment or a `.env` file:

- `AWS_ACCESS_KEY_ID`: Your AWS access key ID
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key
- `AWS_REGION`: The AWS region where your S3 bucket is located (e.g., `ap-southeast-1`)
- `AWS_S3_BUCKET`: The name of your S3 bucket

Example `.env` snippet:

```
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=ap-southeast-1
AWS_S3_BUCKET=your-bucket-name
```

**Note:**
- Make sure your AWS credentials have permission to `PutObject` in the specified bucket.
- Never commit your credentials to version control.
- You must install `boto3` in your environment: `pip install boto3`
