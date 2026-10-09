from dataclasses import dataclass


@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    salary_min: int | None
    salary_max: int | None
    remote: bool
    source: str
    source_id: str | None = None
