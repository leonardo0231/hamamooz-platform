"""Student photo ZIP importer.

Photo filenames are treated as the student national code:
0960402306.jpg -> Student(national_id=0960402306)
"""

from pathlib import Path
from zipfile import ZipFile


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def extract_student_photo_map(zip_file):
    photos = {}
    with ZipFile(zip_file) as archive:
        for member in archive.infolist():
            suffix = Path(member.filename).suffix.lower()
            if suffix not in SUPPORTED_EXTENSIONS:
                continue
            national_id = Path(member.filename).stem.strip()
            if national_id:
                photos[national_id.zfill(10)] = member.filename
    return photos


def match_photos_to_students(students, photo_map):
    """Return students that can be updated with uploaded photos."""
    result = []
    for student in students:
        key = str(student.national_id).zfill(10)
        if key in photo_map:
            result.append((student, photo_map[key]))
    return result
