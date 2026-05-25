from flask import current_app, g, jsonify
import datetime
from werkzeug.exceptions import BadRequest
from . import main_bp
from app.models import WeeklyAdvice, WeeklyAdviceSchema
from app.utils.auth import firebase_auth_required, get_or_create_user
from app.utils.time import latest_monday
from app.utils.exceptions import raise_http_exception


main_bp.route("/api/advices/latest/", defaults={"date_of": None}, methods=["GET"])
@main_bp.route("/api/advices/latest/<string:date_of>", methods=["GET"])
@firebase_auth_required
def get_latest_weekly_advice(date_of):
    """Endpoint to retrieve the advice from the week with date_of for authenticated user.
    - If <date_of> is omitted, returns the advice for the current week.
    - If <date_of> is provided, it should be a date string like '2023-01-02' (YYYY-MM-DD).
    """
    current_app.logger.info("Handling request to retrieve weekly advice.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    # Calculate the Monday of the current week, or the week of the given date if provided.
    start_of_week = latest_monday()
    try:
        # Validate given date formatting then calculates the Monday of that week.
        if date_of:
            sanitized_date = datetime.datetime.strptime(date_of, "%Y-%m-%d").date()
            start_of_week = latest_monday(sanitized_date)
            current_app.logger.info(f"Retrieving advice for week of {start_of_week}.")
    except Exception as e:
        raise ValueError(f"Invalid date format provided: {e}")

    current_app.logger.info(f"The Monday date is {start_of_week}.")
    try:
        # Retrieve the latest weekly advice after sorting by creation date descending.
        advice = WeeklyAdvice.query \
            .filter_by(user_id=user.id, of_week=start_of_week) \
            .order_by(WeeklyAdvice.created_at.desc()) \
            .first()

        # May be possible that the advice generation has occur yet for the current week.
        if not advice:
            current_app.logger.warning(f"User {user.id} has no advice from week {start_of_week}.")
        else:
            current_app.logger.info(f"Retrieved advice from week of {advice.of_week}.")

        serialized_advice = WeeklyAdviceSchema().dump(advice)
        return jsonify({
            "message": f"Successfully retrieved advice for week of {start_of_week}.",
            "advice": serialized_advice
        }), 200

    except ValueError as ve:
        current_app.logger.error(f"Failed to retrieve advice for week with date {date_of}: {ve}")
        raise_http_exception(BadRequest, f"Failed to retrieve advice from week with {date_of}.", str(ve))
    except Exception as e:
        current_app.logger.error(f"Failed to retrieve advice for week of {start_of_week}: {e}")
        raise e
