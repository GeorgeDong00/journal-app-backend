from flask import current_app, g, jsonify
from . import main_bp
from app.models import WeeklyAdvice, WeeklyAdviceSchema
from app.utils.auth import firebase_auth_required, get_or_create_user
from app.utils.time import latest_monday


@main_bp.route("/api/weekly_advice/latest", methods=["GET"])
@firebase_auth_required
def get_latest_weekly_advice():
    """Endpoint to retrieve the latest weekly advice for the authenticated user.

    Request Header:
        Authorization (str): "Bearer <JWT_TOKEN>" (Firebase Auth Token)

    Returns:
        200 OK: Message and serialized latest weekly advice or empty List if no advice is found.

    Raises:
        401 Unauthorized: If the token is invalid or missing.
    """
    current_app.logger.info("Handling request to retrieve latest weekly advice.")
    firebase_uid = g.user["uid"]
    user = get_or_create_user(firebase_uid)

    # Calculate the Monday of the current week.
    start_of_current_week = latest_monday()
    current_app.logger.info(f"Retrieving {user} advice for week of {start_of_current_week}.")

    # Retrieve the latest weekly advice for the user.
    advice = WeeklyAdvice.query.filter_by(user_id=user.id, of_week=start_of_current_week).all()
    current_app.logger.info("Successfully retrieved latest advice.")

    serialized_weekly_advice = WeeklyAdviceSchema(many=True).dump(advice)
    return jsonify({"message": f"Week of {start_of_current_week} has {len(advice)} advice.",
                    "advice": serialized_weekly_advice}), 200
