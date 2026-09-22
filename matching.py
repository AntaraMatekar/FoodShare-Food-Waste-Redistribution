from datetime import datetime


def calculate_match_score(
    food,
    receiver_location=None,
    preferred_category=None,
    requested_quantity=1
):

    score = 0


    # --------------------------------
    # 1. LOCATION MATCH
    # --------------------------------

    if receiver_location and food["location"]:

        if (
            receiver_location.strip().lower()
            ==
            food["location"].strip().lower()
        ):

            score += 40


    # --------------------------------
    # 2. CATEGORY MATCH
    # --------------------------------

    if preferred_category:

        if (
            preferred_category.strip().lower()
            ==
            food["category"].strip().lower()
        ):

            score += 30


    # --------------------------------
    # 3. QUANTITY MATCH
    # --------------------------------

    if food["quantity"] >= requested_quantity:

        score += 20


    # --------------------------------
    # 4. EXPIRY / AVAILABILITY
    # --------------------------------

    try:

        available_until = datetime.strptime(
            food["available_until"],
            "%Y-%m-%dT%H:%M"
        )

        now = datetime.now()

        hours_remaining = (
            available_until - now
        ).total_seconds() / 3600


        if hours_remaining <= 6:

            # Food expiring soon gets priority
            score += 10

        elif hours_remaining <= 24:

            score += 5

    except (ValueError, TypeError):

        pass


    return min(score, 100)
