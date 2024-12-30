from flask import current_app, g, jsonify
from datetime import datetime
from . import main_bp
from app.models import WeeklyAdvice, WeeklyAdviceSchema
from app.utils.auth import firebase_auth_required, get_or_create_user
from app.utils.time import return_previous_sunday


@main_bp.route("/api/weekly_advice/", methods=["GET"])
@firebase_auth_required
def get_weekly_advice():
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

    # Calculate the most recent Sunday date given the current date.
    current_utc_date = datetime.now(datetime.timezone.utc).date()
    latest_sunday = return_previous_sunday(current_utc_date)
    current_app.logger(f"Returned latest Sunday date as {latest_sunday}.")

    # Retrieve the latest weekly advice for the user.
    advice = WeeklyAdvice.query.filter_by(user_id=user.id,
                                          of_week=latest_sunday).first()
    current_app.logger.info(f"Retrieved {advice}.")

    # Empty dictionary is returned if no advice is found.
    serialized_weekly_advice = WeeklyAdviceSchema().dump(advice)
    return jsonify({"message": f"Week of {latest_sunday} has {len(advice)} advice.",
                    "advice": serialized_weekly_advice}), 200
