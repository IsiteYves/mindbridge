import datetime as dt

from app.api import wellness

CHECKINS = "/api/v1/wellness/checkins"


def today():
    return dt.datetime.now(dt.timezone.utc).date()


def save(client, headers, **overrides):
    payload = {"mood": "good", "stress_level": 2}
    payload.update(overrides)
    return client.post(CHECKINS, json=payload, headers=headers)


def test_save_checkin_defaults_to_today(client, make_user_headers):
    headers = make_user_headers("student1")

    response = save(client, headers)

    assert response.status_code == 201
    assert response.get_json() == {
        "id": response.get_json()["id"],
        "checkin_date": today().isoformat(),
        "mood": "good",
        "stress_level": 2,
    }


def test_saving_again_on_the_same_day_updates_the_checkin(client, make_user_headers):
    headers = make_user_headers("student1")
    first = save(client, headers).get_json()

    second = save(client, headers, mood="stressed", stress_level=5)

    assert second.status_code == 200
    assert second.get_json()["id"] == first["id"]
    listed = client.get(CHECKINS, headers=headers).get_json()
    assert len(listed) == 1
    assert listed[0]["mood"] == "stressed"
    assert listed[0]["stress_level"] == 5


def test_save_checkin_accepts_a_recent_past_date(client, make_user_headers):
    headers = make_user_headers("student1")
    yesterday = (today() - dt.timedelta(days=1)).isoformat()

    response = save(client, headers, checkin_date=yesterday)

    assert response.status_code == 201
    assert response.get_json()["checkin_date"] == yesterday


def test_save_checkin_rejects_future_and_old_dates(client, make_user_headers):
    headers = make_user_headers("student1")
    future = (today() + dt.timedelta(days=1)).isoformat()
    too_old = (today() - dt.timedelta(days=wellness.MAX_BACKDATE_DAYS + 1)).isoformat()

    assert save(client, headers, checkin_date=future).status_code == 400
    assert save(client, headers, checkin_date=too_old).status_code == 400
    assert save(client, headers, checkin_date="not-a-date").status_code == 400


def test_save_checkin_rejects_unknown_mood(client, make_user_headers):
    headers = make_user_headers("student1")

    response = save(client, headers, mood="fine")

    assert response.status_code == 400
    assert "mood must be one of" in response.get_json()["error"]


def test_save_checkin_rejects_stress_outside_range(client, make_user_headers):
    headers = make_user_headers("student1")

    for value in (0, 6, "3", 2.5, True, None):
        response = save(client, headers, stress_level=value)
        assert response.status_code == 400, value


def test_list_checkins_returns_the_window_newest_first(client, make_user_headers):
    headers = make_user_headers("student1")
    save(client, headers, checkin_date=(today() - dt.timedelta(days=3)).isoformat())
    save(client, headers, checkin_date=(today() - dt.timedelta(days=1)).isoformat())
    save(client, headers)

    listed = client.get(CHECKINS, query_string={"days": 2}, headers=headers).get_json()

    dates = [item["checkin_date"] for item in listed]
    assert dates == [today().isoformat(), (today() - dt.timedelta(days=1)).isoformat()]


def test_list_checkins_validates_days(client, make_user_headers):
    headers = make_user_headers("student1")

    for value in ("0", "31", "abc"):
        response = client.get(CHECKINS, query_string={"days": value}, headers=headers)
        assert response.status_code == 400, value


def test_checkins_are_private_to_their_owner(client, make_user_headers):
    owner = make_user_headers("owner")
    other = make_user_headers("other")
    save(client, owner)

    assert client.get(CHECKINS, headers=other).get_json() == []


def test_checkin_routes_require_a_token(client):
    assert client.post(CHECKINS, json={"mood": "good", "stress_level": 1}).status_code == 401
    assert client.get(CHECKINS).status_code == 401
