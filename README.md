# Smart Cloud File Manager

A mini-project demonstrating a React + Vite frontend and a Python AWS Lambda backend for serverless cloud file management.

## Features

- Upload files to a private Amazon S3 bucket using short-lived presigned URLs.
- List files using metadata stored in Amazon DynamoDB.
- Download files using short-lived presigned URLs.
- Delete files from the active list while retaining historical S3 versions where applicable.
- View S3 object versions and restore an earlier version.
- Display file size and upload date.

## Project Structure

```text
Smart-Cloud-File-Manager/
├── backend/
│   └── lambda_function.py
├── frontend/
│   ├── src/
│   ├── .env.example
│   ├── index.html
│   ├── package.json
│   └── package-lock.json
├── .gitignore
└── README.md
```

## AWS Resources

Configure the following resources in your AWS account:

1. **Amazon S3:** Create a bucket with Block Public Access enabled and Versioning enabled.
2. **S3 CORS:** Allow the local development origin `http://localhost:5173` with the required PUT, GET, and HEAD methods.
3. **Amazon DynamoDB:** Create a table named `SmartFileMetadata` with partition key `fileId` (String).
4. **AWS IAM:** Create a Lambda execution role with `AWSLambdaBasicExecutionRole` and appropriately scoped S3 and DynamoDB permissions.
5. **AWS Lambda:** Use Python 3.12 and configure the handler as `lambda_function.handler`.
6. **Lambda environment variables:**
   - `BUCKET_NAME`: Your S3 bucket name.
   - `TABLE_NAME`: `SmartFileMetadata`.
   - `ALLOWED_ORIGIN`: `http://localhost:5173`.
7. **Amazon API Gateway:** Create an HTTP API connected to Lambda with the required routes and CORS settings.
8. **Frontend configuration:** Set `VITE_API_BASE_URL` to your API Gateway invoke URL in the local frontend `.env` file.

The Lambda execution role should grant only the permissions needed by this application.

## Deploy the Lambda Backend

Create an AWS Lambda function using Python 3.12. Upload `backend/lambda_function.py` or paste its contents into the Lambda editor.

Set the handler to:

```text
lambda_function.handler
```

Configure the execution role and the environment variables listed above. Review the deployed code and permissions before testing.

## Run the Frontend Locally

Install Node.js LTS.

Open a terminal in the `frontend` directory and run:

```bash
npm install
```

Create a local `.env` file from the example.

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set the actual API Gateway URL:

```text
VITE_API_BASE_URL=https://YOUR_API_ID.execute-api.YOUR_REGION.amazonaws.com
```

Then start the development server:

```bash
npm run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173`.

**Do not commit your real `.env` file or AWS credentials.** The `.env.example` file should contain placeholders only.

## Testing Checklist

- Upload a small test file.
- Confirm the file appears in the application list.
- Download the uploaded file.
- Delete a disposable test file and confirm it disappears from the active list.
- Test version listing using an object that has multiple S3 versions.
- Test restoring an earlier version.

The starter application creates a unique S3 key for each uploaded file. Consequently, uploading the same filename again may not create another version of the same object key. Test version history against an object that actually has multiple versions.

## Security and Limitations

This is an educational mini-project, not a production-ready file-sharing service.

- User authentication and per-user authorization are not implemented.
- Do not store confidential files or expose the application publicly without additional security controls.
- Consider Amazon Cognito or another suitable authentication mechanism and enforce ownership checks for file operations.
- Presigned URLs act as bearer tokens. Do not log or share them.
- The demonstration limits file uploads to 10 MB and scans the DynamoDB table, making it suitable only for small demonstrations.
- Review AWS pricing, storage usage, and billing alerts before deployment.

Delete unused AWS resources when the demonstration is complete to reduce the possibility of ongoing charges.

## Technologies Used

- React and Vite
- Python and AWS Lambda
- Amazon API Gateway
- Amazon S3
- Amazon DynamoDB
- AWS IAM

## Repository

GitHub repository: `Fiile_Manager_AWS`


