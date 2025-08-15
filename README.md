# AWS Rekognition Label Detection

This project demonstrates how to use **Amazon Rekognition** with **Boto3** to detect labels and confidence scores for images stored in an **Amazon S3 bucket**.  

The script:
1. Reads a list of images already uploaded to an S3 bucket.
2. Calls `detect_labels` from Amazon Rekognition on each image.
3. Saves the results in:
   - `labels.csv` (tabular summary)
   - `labels.json` (combined JSON)
   - `results_json/` (individual JSON files for each image)

---

## 🚀 How It Works

1. **Upload Images to S3**  
   Upload your images (e.g., cats, burgers, bikes) directly to your S3 bucket via the AWS Console or AWS CLI.  
   Ensure your IAM user has both **Amazon Rekognition** and **S3 full access** permissions.

2. **Run the Script**  
   ```bash
   python rekognition_detect_labels.py
   ```
    The script will:

    - Loop through all images in the specified S3 bucket.

    - Call Rekognition to detect labels and confidence scores.

    - Save the results locally in CSV and JSON formats.

3. **View Results**

    `labels.csv` → All image labels in a spreadsheet-friendly format.

    `labels.json` → All labels in a single JSON file.

    `results_json/` → Separate JSON file for each image.

---

## 📂 Project Structure

| File / Folder                  | Description |
|--------------------------------|-------------|
| `detect_labels.py` | Main Python script for uploading images and detecting labels. |
| `README.md`                    | Documentation for setup, usage, and output details. |
| `results_json/`                | Folder containing per-image JSON results with detected labels and confidence scores. |
| `labels.csv`                   | Combined CSV report of detected labels for all images. |
| `labels.json`                  | Combined JSON report of detected labels for all images. |
| `sample_images/`               | Folder with example images for testing (e.g., cats, burgers, bikes). |

## 📝 Example Output (from labels.csv)

![alt text](image.png)

## 🔐 IAM Permissions Required

- AmazonS3FullAccess

- AmazonRekognitionFullAccess
