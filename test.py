import requests
import mimetypes

def get_presigned_url(endpoint):
    """
    Fetches a pre-signed URL from a given endpoint.

    Parameters:
        endpoint (str): The URL of the endpoint to request the pre-signed URL.

    Returns:
        str: The pre-signed URL.
    """
    try:
        response = requests.get(endpoint)

        if response.status_code == 200:
            presigned_url = response.json().get("url")
            if presigned_url:
                return presigned_url
            else:
                raise ValueError("Pre-signed URL not found in the response.")
        else:
            raise Exception(f"Failed to fetch pre-signed URL. Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error fetching pre-signed URL: {e}")
        raise


def get_mime_type(file_path):
    """
    Determines the MIME type of a file.

    Parameters:
        file_path (str): The local path to the file.

    Returns:
        str: The MIME type of the file.
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"  # Default to a generic binary stream


def upload_file_with_presigned_url(presigned_url, file_path):
    """
    Uploads a file to S3 using a pre-signed URL.

    Parameters:
        presigned_url (str): The pre-signed URL for S3 upload.
        file_path (str): The local path to the file to be uploaded.

    Returns:
        str: Success message or error message.
    """
    try:
        # Read the file in binary mode
        with open(file_path, "rb") as file:
            file_data = file.read()

        # Determine the file's MIME type
        content_type = get_mime_type(file_path)

        # Make the PUT request to upload the file
        response = requests.put(
            presigned_url,
            data=file_data,
            headers={"Content-Type": content_type},
        )

        # Check the response status
        if response.status_code == 200:
            print("File uploaded successfully!")
            return "File uploaded successfully!"
        else:
            print(f"Failed to upload file. Status code: {response.status_code}, Response: {response.text}")
            return f"Failed to upload file. Status code: {response.status_code}, Response: {response.text}"

    except FileNotFoundError:
        print("Error: The file was not found.")
        return "Error: File not found."
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}"


# Define the endpoint and file path
file_path = "./logo.png"
file_name = "logo.png"

# Extract MIME type for pre-signed URL generation
content_type = get_mime_type(file_path)
presigned_url_endpoint = f"http://localhost:8000/api/generate_presigned_url?file_name={file_name}&content_type={content_type}"

try:
    # Fetch the presigned URL
    presigned_url = get_presigned_url(presigned_url_endpoint)
    print(f"Fetched pre-signed URL: {presigned_url}")

    # Upload the file using the pre-signed URL
    upload_file_with_presigned_url(presigned_url, file_path)

except Exception as e:
    print(f"An error occurred: {e}")
