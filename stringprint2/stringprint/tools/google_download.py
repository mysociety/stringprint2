import io
import json
import os
from pathlib import Path
from typing import Optional, Union

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from oauth2client.service_account import ServiceAccountCredentials


class GoogleDownloader:

    mime_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    def __init__(self):

        data = os.environ.get("GDRIVE_SERVICE_USER", None)
        if data is None:
            raise ValueError("GDRIVE_SERVICE_USER env var not set.")

        credentials = json.loads(data)

        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            credentials,
            [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        self.drive_service = build("drive", "v3", credentials=credentials)

    def download_file(
        self,
        *,
        dest: Union[str, Path],
        google_id: Optional[str] = None,
        url: Optional[str] = None,
        mime_type: Optional[str] = None,
    ):
        """
        url takes precidence over google_id
        if mime_type not specified, will try and work out from destination extention

        """

        if not (google_id or url):
            raise ValueError("Must specify google id or url of file to download")

        if url:
            # assuming the edit view
            google_id = url.split("/")[-2]

        if isinstance(dest, str):
            dest = Path(dest)

        if mime_type is None:
            mime_type = self.__class__.mime_types.get(dest.suffix, None)

        if mime_type is None:
            raise ValueError(f"Can't extract a mimetype from {dest.suffix}")

        request = self.drive_service.files().export_media(
            fileId=google_id, mimeType=mime_type
        )
        fh = io.FileIO(dest, "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        print(f"waiting for download of {dest.name} start")
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")
        print("Download Finished.")
