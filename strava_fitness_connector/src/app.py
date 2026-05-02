from datetime import datetime, timedelta, timezone
import threading
import time

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .config import settings
from .db import Base, engine, get_db
from .importer import ActivityImporter
from .models import Activity, Athlete, SyncState
from .schemas import HealthResponse, ImportResponse
from .strava_client import StravaClient

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)


@app.get("/")
def root(db: Session = Depends(get_db)):
    athlete = db.query(Athlete).order_by(Athlete.id.asc()).first()
    if athlete is None:
        return RedirectResponse(url="/auth/login")
    return RedirectResponse(url="/docs")


HIKING_TYPES = {"hike", "hiking", "trekking", "escursionismo"}
BIKE_TYPES = {"ride", "bikeride", "virtualride", "ebikeride", "mountainbikeride", "gravelride", "indoorcycling", "spinning", "bike", "cycling"}
SPORT_WALK_TYPES = {"walk", "walking", "racewalk", "sportwalk", "camminata", "camminatasportiva"}
YOGA_MEDITATION_TYPES = {"yoga", "meditation", "meditazione"}
TENNIS_PADEL_TYPES = {"tennis", "padel", "paddle", "racquetsport", "racketsport"}


def normalize_activity_type(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value.lower() if ch.isalnum())


def activity_matches(activity: Activity, categories: set[str]) -> bool:
    searchable_values = [activity.sport_type, activity.type, activity.name]
    return any(normalize_activity_type(value) in categories for value in searchable_values)


def parse_strava_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def meters_to_km(value: float | None) -> float:
    return round((value or 0.0) / 1000, 2)


def seconds_to_hours(value: int | None) -> float:
    return round((value or 0) / 3600, 2)


def calculate_intensity_factor(avg_hr: float | None) -> float:
    if avg_hr is None:
        return 1.0
    if avg_hr < 100:
        return 1.0
    if avg_hr < 120:
        return 1.2
    if avg_hr < 140:
        return 1.5
    if avg_hr < 160:
        return 1.8
    return 2.2


def calculate_estimated_training_load(activity: Activity) -> float:
    duration_minutes = (activity.moving_time or 0) / 60
    intensity_factor = calculate_intensity_factor(activity.average_heartrate)
    return duration_minutes * intensity_factor


def summarize_activities(activities: list[Activity]) -> dict:
    total_distance = 0.0
    hiking_distance = 0.0
    bike_distance = 0.0
    sport_walk_distance = 0.0
    yoga_meditation_time = 0
    tennis_padel_time = 0
    tennis_padel_count = 0
    total_time = 0
    total_elevation = 0.0
    hr_weighted_sum = 0.0
    hr_weight_seconds = 0
    training_load = 0.0
    active_days: set[str] = set()

    for activity in activities:
        start_date = parse_strava_datetime(activity.start_date)
        if start_date:
            active_days.add(start_date.date().isoformat())

        distance = activity.distance or 0.0
        moving_time = activity.moving_time or 0
        elevation = activity.total_elevation_gain or 0.0

        total_distance += distance
        total_time += moving_time
        total_elevation += elevation
        training_load += calculate_estimated_training_load(activity)

        if activity.average_heartrate is not None and moving_time > 0:
            hr_weighted_sum += activity.average_heartrate * moving_time
            hr_weight_seconds += moving_time

        if activity_matches(activity, HIKING_TYPES):
            hiking_distance += distance
        elif activity_matches(activity, BIKE_TYPES):
            bike_distance += distance
        elif activity_matches(activity, SPORT_WALK_TYPES):
            sport_walk_distance += distance

        if activity_matches(activity, YOGA_MEDITATION_TYPES):
            yoga_meditation_time += moving_time

        if activity_matches(activity, TENNIS_PADEL_TYPES):
            tennis_padel_time += moving_time
            tennis_padel_count += 1

    return {
        "activities_count": len(activities),
        "total_distance_km": meters_to_km(total_distance),
        "hiking_trekking_distance_km": meters_to_km(hiking_distance),
        "bike_distance_km": meters_to_km(bike_distance),
        "sport_walk_distance_km": meters_to_km(sport_walk_distance),
        "yoga_meditation_time_hours": seconds_to_hours(yoga_meditation_time),
        "tennis_padel_activities_count": tennis_padel_count,
        "tennis_padel_time_hours": seconds_to_hours(tennis_padel_time),
        "total_time_hours": seconds_to_hours(total_time),
        "total_elevation_gain_m": round(total_elevation, 0),
        "average_heart_rate_bpm": round(hr_weighted_sum / hr_weight_seconds, 1) if hr_weight_seconds else None,
        "heart_rate_duration_hours": seconds_to_hours(hr_weight_seconds),
        "estimated_training_load": round(training_load, 1),
        "active_days": len(active_days),
    }


def load_activities_between(db: Session, start: datetime, end: datetime) -> list[Activity]:
    rows = db.query(Activity).all()
    result: list[Activity] = []

    for row in rows:
        start_date = parse_strava_datetime(row.start_date)
        if start_date and start <= start_date < end:
            result.append(row)

    return result


def percentage_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


def safe_ratio(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return current / previous


def add_insight(insights: list[dict], category: str, severity: str, message: str, suggestion: str | None = None) -> None:
    item = {"category": category, "severity": severity, "message": message}
    if suggestion:
        item["suggestion"] = suggestion
    insights.append(item)


def build_rule_based_insights(current: dict, previous: dict, ytd_average: dict) -> list[dict]:
    insights: list[dict] = []

    load_change_prev = percentage_change(current["estimated_training_load"], previous["estimated_training_load"])
    load_change_ytd = percentage_change(current["estimated_training_load"], ytd_average["estimated_training_load"])
    distance_change_prev = percentage_change(current["total_distance_km"], previous["total_distance_km"])
    active_days_delta = current["active_days"] - previous["active_days"]

    if load_change_prev is not None:
        if load_change_prev > 25:
            add_insight(
                insights,
                "training_load",
                "warning",
                f"Il carico stimato del mese corrente è aumentato del {load_change_prev}% rispetto al mese precedente.",
                "Valuta di distribuire meglio il carico o inserire recupero se percepisci stanchezza.",
            )
        elif load_change_prev < -25:
            add_insight(
                insights,
                "training_load",
                "info",
                f"Il carico stimato del mese corrente è diminuito del {abs(load_change_prev)}% rispetto al mese precedente.",
                "Può essere una fase di scarico utile; verifica però che sia coerente con i tuoi obiettivi.",
            )
        else:
            add_insight(
                insights,
                "training_load",
                "positive",
                f"Il carico stimato è relativamente stabile rispetto al mese precedente ({load_change_prev}%).",
                "La stabilità del carico è una buona base per costruire progressi sostenibili.",
            )

    if load_change_ytd is not None:
        if load_change_ytd > 20:
            add_insight(
                insights,
                "ytd_comparison",
                "info",
                f"Il mese corrente è sopra la tua media mensile da inizio anno del {load_change_ytd}% sul carico stimato.",
                "Buon segnale se accompagnato da recupero adeguato e assenza di fastidi.",
            )
        elif load_change_ytd < -20:
            add_insight(
                insights,
                "ytd_comparison",
                "info",
                f"Il mese corrente è sotto la tua media mensile da inizio anno del {abs(load_change_ytd)}% sul carico stimato.",
                "Potrebbe essere un mese più leggero: utile se pianificato, da correggere se non voluto.",
            )

    if distance_change_prev is not None and abs(distance_change_prev) >= 20:
        direction = "aumentata" if distance_change_prev > 0 else "diminuita"
        add_insight(
            insights,
            "volume",
            "info",
            f"La distanza totale è {direction} del {abs(distance_change_prev)}% rispetto al mese precedente.",
            "Osserva se il cambio di volume è coerente con energia, recupero e qualità degli allenamenti.",
        )

    if active_days_delta >= 3:
        add_insight(
            insights,
            "consistency",
            "positive",
            f"Hai aumentato la consistenza: {current['active_days']} giorni attivi nel mese corrente, {active_days_delta} in più del mese precedente.",
            "Distribuire le attività su più giorni aiuta a ridurre picchi di carico.",
        )
    elif active_days_delta <= -3:
        add_insight(
            insights,
            "consistency",
            "info",
            f"La consistenza è calata: {current['active_days']} giorni attivi nel mese corrente, {abs(active_days_delta)} in meno del mese precedente.",
            "Può essere utile ripristinare micro-sessioni leggere per mantenere continuità.",
        )

    padel_ratio = safe_ratio(current["tennis_padel_time_hours"], current["total_time_hours"])
    if padel_ratio is not None and padel_ratio >= 0.25:
        add_insight(
            insights,
            "high_intensity_mix",
            "info",
            f"Padel/tennis pesa circa il {round(padel_ratio * 100, 1)}% del tempo totale del mese corrente.",
            "È una componente intensa e intermittente: bilanciala con recupero e lavoro aerobico leggero.",
        )

    recovery_ratio = safe_ratio(current["yoga_meditation_time_hours"], current["total_time_hours"])
    if recovery_ratio is not None and recovery_ratio >= 0.15:
        add_insight(
            insights,
            "recovery",
            "positive",
            f"Yoga/meditazione rappresenta circa il {round(recovery_ratio * 100, 1)}% del tempo totale del mese corrente.",
            "Buon equilibrio tra attività e recupero attivo.",
        )

    if not insights:
        add_insight(
            insights,
            "summary",
            "info",
            "Non emergono variazioni forti rispetto ai riferimenti disponibili.",
            "Continua a monitorare volume, carico stimato e consistenza.",
        )

    return insights


def background_sync():
    while True:
        try:
            db_gen = get_db()
            db = next(db_gen)

            athlete = db.query(Athlete).order_by(Athlete.id.asc()).first()
            if athlete:
                importer = ActivityImporter(db)
                imported, _ = importer.sync_incremental(athlete.id)
                print(f"[SYNC] Imported {imported} new activities")

            db.close()
        except Exception as e:
            print("[SYNC ERROR]", e)

        time.sleep(settings.sync_interval_seconds)


@app.on_event("startup")
def start_background_sync():
    if settings.sync_enabled:
        thread = threading.Thread(target=background_sync, daemon=True)
        thread.start()
        print(f"[SYNC] Background sync started every {settings.sync_interval_seconds} seconds")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/auth/login")
def auth_login(db: Session = Depends(get_db)):
    client = StravaClient(db)
    url = client.build_authorize_url()
    return RedirectResponse(url=url)


@app.get("/auth/callback")
def auth_callback(code: str, scope: str | None = None, db: Session = Depends(get_db)):
    if not settings.strava_client_id or not settings.strava_client_secret:
        raise HTTPException(status_code=500, detail="Missing Strava credentials in .env")

    client = StravaClient(db)
    payload = client.exchange_code_for_token(code)
    client.upsert_token_payload(payload, accepted_scope=scope)
    return RedirectResponse(url="/docs")


@app.get("/athlete")
def get_athlete(db: Session = Depends(get_db)):
    athlete = db.query(Athlete).order_by(Athlete.id.asc()).first()
    if athlete is None:
        raise HTTPException(status_code=404, detail="No athlete authenticated yet")
    return {
        "id": athlete.id,
        "firstname": athlete.firstname,
        "lastname": athlete.lastname,
        "city": athlete.city,
        "state": athlete.state,
        "country": athlete.country,
    }


@app.post("/import/activities", response_model=ImportResponse)
def import_activities(
    max_pages: int = Query(default=10, ge=1, le=100),
    per_page: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ImportResponse:
    athlete = db.query(Athlete).order_by(Athlete.id.asc()).first()
    if athlete is None:
        raise HTTPException(status_code=404, detail="Authenticate first at /auth/login")

    importer = ActivityImporter(db)
    imported, pages = importer.import_activities(athlete_id=athlete.id, max_pages=max_pages, per_page=per_page)
    return ImportResponse(imported=imported, pages=pages)


@app.post("/sync/incremental")
def sync_incremental(
    per_page: int = Query(default=200, ge=1, le=200),
    overlap_seconds: int = Query(default=86400, ge=0, le=604800),
    db: Session = Depends(get_db),
):
    athlete = db.query(Athlete).order_by(Athlete.id.asc()).first()
    if athlete is None:
        raise HTTPException(status_code=404, detail="Authenticate first at /auth/login")

    importer = ActivityImporter(db)
    imported, pages = importer.sync_incremental(
        athlete_id=athlete.id,
        per_page=per_page,
        overlap_seconds=overlap_seconds,
    )

    sync_state = db.get(SyncState, 1)

    return {
        "message": "Incremental sync completed",
        "imported": imported,
        "pages": pages,
        "last_sync_at": sync_state.last_sync_at if sync_state else None,
        "last_activity_start_date": sync_state.last_activity_start_date if sync_state else None,
    }


@app.get("/activities")
def list_activities(limit: int = Query(default=20, ge=1, le=200), db: Session = Depends(get_db)):
    rows = db.query(Activity).order_by(Activity.start_date.desc()).limit(limit).all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "sport_type": row.sport_type,
            "start_date": row.start_date,
            "distance": row.distance,
            "moving_time": row.moving_time,
            "average_heartrate": row.average_heartrate,
            "total_elevation_gain": row.total_elevation_gain,
        }
        for row in rows
    ]


@app.get("/activities/count")
def count_activities(db: Session = Depends(get_db)):
    return {"count": db.query(Activity).count()}


@app.get("/stats/ytd")
def stats_year_to_date(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    ytd_activities = load_activities_between(db, year_start, now + timedelta(seconds=1))

    return {
        "period": {
            "from": year_start.isoformat(),
            "to": now.isoformat(),
        },
        **summarize_activities(ytd_activities),
    }


@app.get("/stats/weekly")
def stats_weekly(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    current_week_start = datetime.combine((now - timedelta(days=now.weekday())).date(), datetime.min.time(), tzinfo=timezone.utc)
    current_week_end = current_week_start + timedelta(days=7)
    previous_week_start = current_week_start - timedelta(days=7)

    current_activities = load_activities_between(db, current_week_start, current_week_end)
    previous_activities = load_activities_between(db, previous_week_start, current_week_start)

    current_summary = summarize_activities(current_activities)
    previous_summary = summarize_activities(previous_activities)

    return {
        "current_week": {
            "week": f"{current_week_start.isocalendar().year}-W{current_week_start.isocalendar().week:02d}",
            "from": current_week_start.isoformat(),
            "to": current_week_end.isoformat(),
            **current_summary,
        },
        "previous_week": {
            "week": f"{previous_week_start.isocalendar().year}-W{previous_week_start.isocalendar().week:02d}",
            "from": previous_week_start.isoformat(),
            "to": current_week_start.isoformat(),
            **previous_summary,
        },
        "trend_vs_previous_week": {
            "distance_percent": percentage_change(current_summary["total_distance_km"], previous_summary["total_distance_km"]),
            "time_percent": percentage_change(current_summary["total_time_hours"], previous_summary["total_time_hours"]),
            "training_load_percent": percentage_change(current_summary["estimated_training_load"], previous_summary["estimated_training_load"]),
            "activities_delta": current_summary["activities_count"] - previous_summary["activities_count"],
            "active_days_delta": current_summary["active_days"] - previous_summary["active_days"],
        },
        "notes": {
            "estimated_training_load": "duration_minutes multiplied by an HR-based intensity factor. It is a proxy, not the official Strava/Amazfit training load.",
            "heart_rate_average": "time-weighted average heart rate over activities with HR data.",
        },
    }


@app.get("/insights/summary")
def insights_summary(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    current_month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 1:
        previous_month_start = datetime(now.year - 1, 12, 1, tzinfo=timezone.utc)
    else:
        previous_month_start = datetime(now.year, now.month - 1, 1, tzinfo=timezone.utc)
    year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)

    current_month_activities = load_activities_between(db, current_month_start, now + timedelta(seconds=1))
    previous_month_activities = load_activities_between(db, previous_month_start, current_month_start)
    ytd_activities = load_activities_between(db, year_start, now + timedelta(seconds=1))

    current_summary = summarize_activities(current_month_activities)
    previous_summary = summarize_activities(previous_month_activities)
    ytd_summary = summarize_activities(ytd_activities)

    months_elapsed = max(1, now.month)
    ytd_average = {
        key: round(value / months_elapsed, 2) if isinstance(value, (int, float)) else value
        for key, value in ytd_summary.items()
    }

    return {
        "period": {
            "current_month": current_month_start.strftime("%Y-%m"),
            "previous_month": previous_month_start.strftime("%Y-%m"),
            "ytd_from": year_start.isoformat(),
            "generated_at": now.isoformat(),
        },
        "current_month": current_summary,
        "previous_month": previous_summary,
        "ytd_monthly_average": ytd_average,
        "insights": build_rule_based_insights(current_summary, previous_summary, ytd_average),
        "notes": {
            "method": "Rule-based insights. No AI model is used at this stage.",
            "training_load": "Estimated from duration and average HR. It is not the official Strava/Amazfit training load.",
        },
    }
