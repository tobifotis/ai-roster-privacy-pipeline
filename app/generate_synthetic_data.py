"""Generate synthetic OneRoster-style CSV files, one folder per school district.

All data is synthetic. No real students or real personal information is used.
"""
import csv
import json
import random
from datetime import date
from pathlib import Path

from faker import Faker

SEED = 42
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DISTRICTS = {
    "district_a": "Lincoln Unified School District",
    "district_b": "Riverside County Schools",
}
SCHOOLS_PER_DISTRICT = 2
TEACHERS_PER_SCHOOL = 4
STUDENTS_PER_SCHOOL = 40
SUBJECTS = ["Math", "English", "Science", "History"]
NOW = "2026-10-26T00:00:00Z"
TODAY = date(2026, 10, 26)

# (note text, which private details it contains)
NOTE_TEMPLATES = [
    ("{student}'s mom {parent} called about the bus.", ["student", "parent"]),
    ("Please call {parent} at {phone} about {student}'s absence.", ["parent", "phone", "student"]),
    ("{student} moved to {address}. Update the bus route.", ["student", "address"]),
    ("Parent email is {email}, prefers messages after 5pm.", ["email"]),
    ("{student} did great on the fractions quiz today.", ["student"]),
    ("Reminder: library books are due Friday.", []),
]

gen = Faker("en_US")
Faker.seed(SEED)
random.seed(SEED)


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def build_district(key, district_name):
    out = DATA_DIR / key
    district_id = f"{key}-org"
    orgs = [[district_id, "active", NOW, district_name, "district", key, ""]]
    users, demographics, classes, enrollments, notes = [], [], [], [], []

    for s in range(1, SCHOOLS_PER_DISTRICT + 1):
        school_id = f"{key}-school-{s}"
        school_name = f"{gen.last_name()} {random.choice(['Elementary', 'Middle School', 'High School'])}"
        orgs.append([school_id, "active", NOW, school_name, "school", f"{key}-S{s}", district_id])

        class_ids = []
        for t in range(1, TEACHERS_PER_SCHOOL + 1):
            teacher_id = f"{key}-teacher-{s}-{t}"
            first, last = gen.first_name(), gen.last_name()
            username = f"{first}.{last}".lower()
            users.append([teacher_id, "active", NOW, "true", school_id, "teacher",
                          username, first, last, f"T{s}{t:03d}", f"{username}@school.example", "", ""])
            subject = SUBJECTS[(t - 1) % len(SUBJECTS)]
            class_id = f"{key}-class-{s}-{t}"
            class_ids.append(class_id)
            classes.append([class_id, "active", NOW, subject, f"{subject[:4].upper()}-{s}{t}", "scheduled", school_id])
            enrollments.append([f"{class_id}-enr-teacher", "active", NOW, class_id, school_id,
                                teacher_id, "teacher", "true", "2026-08-15", ""])

        for n in range(1, STUDENTS_PER_SCHOOL + 1):
            student_id = f"{key}-student-{s}-{n:03d}"
            first, last = gen.first_name(), gen.last_name()
            dob = gen.date_of_birth(minimum_age=6, maximum_age=17)
            grade = min(12, max(1, (TODAY - dob).days // 365 - 5))
            username = f"{first}.{last}{n}".lower()
            users.append([student_id, "active", NOW, "true", school_id, "student",
                          username, first, last, f"S{s}{n:04d}", f"{username}@student.example", "", grade])
            demographics.append([student_id, "active", NOW, dob.isoformat(), random.choice(["female", "male"])])
            for class_id in random.sample(class_ids, 3):
                enrollments.append([f"{class_id}-enr-{student_id}", "active", NOW, class_id, school_id,
                                    student_id, "student", "false", "2026-08-15", ""])

            parent_first = gen.first_name()
            values = {
                "student": f"{first} {last}",
                "parent": f"{parent_first} {last}",
                "phone": gen.phone_number(),
                "address": f"{gen.street_address()}, {gen.city()}",
                "email": f"{parent_first}.{last}@example.com".lower(),
            }
            template, keys = random.choice(NOTE_TEMPLATES)
            notes.append([f"{student_id}-note", student_id, template.format(**values),
                          json.dumps([values[k] for k in keys])])

    write_csv(out / "orgs.csv", ["sourcedId", "status", "dateLastModified", "name", "type", "identifier", "parentSourcedId"], orgs)
    write_csv(out / "users.csv", ["sourcedId", "status", "dateLastModified", "enabledUser", "orgSourcedIds", "role",
                                  "username", "givenName", "familyName", "identifier", "email", "phone", "grades"], users)
    write_csv(out / "demographics.csv", ["sourcedId", "status", "dateLastModified", "birthDate", "sex"], demographics)
    write_csv(out / "classes.csv", ["sourcedId", "status", "dateLastModified", "title", "classCode", "classType", "schoolSourcedId"], classes)
    write_csv(out / "enrollments.csv", ["sourcedId", "status", "dateLastModified", "classSourcedId", "schoolSourcedId",
                                        "userSourcedId", "role", "primary", "beginDate", "endDate"], enrollments)
    write_csv(out / "notes.csv", ["noteId", "studentSourcedId", "text", "pii_labels"], notes)
    print(f"{key}: {len(users)} users, {len(classes)} classes, {len(enrollments)} enrollments, {len(notes)} notes")


if __name__ == "__main__":
    for district_key, district_name in DISTRICTS.items():
        build_district(district_key, district_name)