from urllib.parse import urlparse

import requests

REQUEST_TIMEOUT = 10
PAGE_SIZE = 100
MAX_TITLE_LENGTH = 255


class CanvasError(Exception):
    def __init__(self, message, status_code):
        super().__init__(message)
        self.status_code = status_code


class CanvasClient:
    def __init__(self, base_url, token, session=None):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    def list_courses(self):
        courses = self._get_all("/api/v1/courses", {"enrollment_state": "active"})
        return [
            {"id": str(course["id"]), "name": course["name"][:MAX_TITLE_LENGTH]}
            for course in courses
            if course.get("id") is not None and course.get("name")
        ]

    def list_assignments(self, course_id):
        items = self._get_all(f"/api/v1/courses/{course_id}/assignments", {"include[]": "rubric"})
        return [_normalize(item, course_id) for item in items]

    def _get_all(self, path, params):
        url = f"{self.base_url}{path}"
        params = {"per_page": PAGE_SIZE, **params}
        results = []
        while url:
            response = self._get(url, params)
            try:
                page = response.json()
            except ValueError:
                raise CanvasError("Canvas returned an unreadable response", 502) from None
            if not isinstance(page, list):
                raise CanvasError("Canvas returned an unexpected response", 502)
            results.extend(page)
            url = self._next_url(response)
            params = None
        return results

    def _get(self, url, params):
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        except requests.RequestException:
            raise CanvasError("Could not reach Canvas", 502) from None
        if response.status_code in (401, 403):
            raise CanvasError("Canvas rejected the access token or its permissions", 401)
        if not response.ok:
            raise CanvasError("Canvas returned an error", 502)
        return response

    def _next_url(self, response):
        url = response.links.get("next", {}).get("url")
        if url:
            base, target = urlparse(self.base_url), urlparse(url)
            if (target.scheme, target.netloc) != (base.scheme, base.netloc):
                raise CanvasError("Canvas pagination pointed to an unexpected host", 502)
        return url


def _normalize(item, course_id):
    return {
        "canvas_id": str(item["id"]),
        "course_id": str(course_id),
        "title": (item.get("name") or "Untitled assignment")[:MAX_TITLE_LENGTH],
        "deadline": item.get("due_at"),
        "rubric": [
            {
                "title": (criterion.get("description") or "Criterion")[:MAX_TITLE_LENGTH],
                "points": criterion.get("points"),
            }
            for criterion in item.get("rubric") or []
        ],
    }
