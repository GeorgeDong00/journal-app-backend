from flask import current_app, g, jsonify
from . import main_bp
from app.models import WeeklyAdvice, WeeklyAdviceSchema
from app.utils.auth import firebase_auth_required, get_or_create_user
from app.utils.time import latest_monday


@main_bp.route("/api/advice/latest", methods=["GET"])
@firebase_auth_required
def get_latest_weekly_advice():
    """Endpoint to retrieve the latest weekly advice for the authenticated user."""
    current_app.logger.info("Handling request to retrieve latest weekly advice.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    # Calculate the Monday of the current week.
    start_of_current_week = latest_monday()
    current_app.logger.info(f"This Monday date is {start_of_current_week}.")

    try:
        # Retrieve the latest weekly advice for the user.
        advice = WeeklyAdvice.query.filter_by(user_id=user.id,
                                              of_week=start_of_current_week).first()

        # May be possible that the advice generation has occur yet for the current week.
        if not advice:
            current_app.logger.warning(f"User {user.id} has no advice from latest week {start_of_current_week}.")
        else:
            current_app.logger.info(f"Retrieved latest advice from week of {advice.of_week}.")

        serialized_advice = WeeklyAdviceSchema().dump(advice)
        return jsonify({
            "message": f"Successfully retrieved latest advice for week of {start_of_current_week}.",
            "advice": serialized_advice
        }), 200

    except Exception as e:
        current_app.logger.error(f"Failed to retrieve latest advice for week of {start_of_current_week}: {e}")
        raise e
