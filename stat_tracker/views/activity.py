from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from io import BytesIO
from flask import Blueprint, flash, render_template, redirect, url_for, send_file
from flask.ext.login import current_user, login_required
from ..forms import ActivityForm
from ..models import Activity, Timestamp
from ..extensions import db


activity = Blueprint("activity", __name__)

@activity.route("/<user>/<activity_name>/visualize", methods=['GET', 'POST'])
@login_required
def visualize(user, activity_name):
    fig = create_plot(user, activity_name)
    return send_file(fig, mimetype="image/png")

@activity.route("/<user>/<activity_name>/check", methods=['POST'])
@login_required
def check(user, activity_name):
    checked_activity = Activity.query.filter_by(name=activity_name).filter_by(creator=user).first()
    today = datetime.today().strftime("%Y-%m-%d")
    timestamp = Timestamp.query.filter_by(activity_id=checked_activity.id, actor_id=user, timestamp=today).first()
    if checked_activity and not timestamp:
        timestamp = Timestamp(activity_id=checked_activity.id, actor_id=user, timestamp=today)
        db.session.add(timestamp)
        db.session.commit()
    return redirect(url_for("activity.list", user=user))


@activity.route("/<user>/add", methods=['GET', 'POST'])
@login_required
def add(user):
    form = ActivityForm()
    if form.validate_on_submit():
        new_activity = Activity.query.filter_by(name=form.name.data).filter_by(creator=user).first()
        if new_activity:
            flash("Activity already exists.")
        else:
            print("\n\nForm: ", form.type.data)
            new_activity = Activity(name=form.name.data,
                                    description=form.description.data,
                                    activity_type=form.type.data,
                                    creator=user)
            db.session.add(new_activity)
            db.session.commit()
            flash("Activity Added!")
            return redirect(url_for("activity.list", user=user))
    elif form.is_submitted():
        flash("Something must be weird. Try again.")
    return render_template("activityform.html", user=user, form=form, source="add")

@activity.route("/<user>/list")
@login_required
def list(user):
    activities = Activity.query.filter_by(creator=user).all()
    today = datetime.today().strftime("%Y-%m-%d")
    checked_in_today = db.session.query(Timestamp.activity_id).filter_by(actor_id=user, timestamp=today).all()
    checked_in_today = [item[0] for item in checked_in_today]
    print("Type: ",checked_in_today)
    print(activities)
    return render_template("list.html",
                           user=user,
                           activities=activities,
                           checked_in_today=checked_in_today)

@activity.route("/<user>/<activity_name>", methods=['GET', 'POST'])
@login_required
def details(user, activity_name):
    original_activity = Activity.query.filter_by(name=activity_name).filter_by(creator=user).first()
    form = ActivityForm(name=original_activity.name,
                        description=original_activity.description,
                        type=original_activity.activity_type)
    if form.validate_on_submit():
        new_activity = Activity.query.filter_by(name=activity_name).filter_by(creator=user).first()
        new_activity.name = form.name.data,
        new_activity.description = form.description.data,
        new_activity.activity_type = form.type.data
        db.session.commit()
        flash("Activity Details Saved!")
        return redirect(url_for("activity.list", user=user))

    elif form.is_submitted():
        flash("Something must be weird. Try again.")
    return render_template("activityform.html",
                           user=user,
                           form=form,
                           source="details",
                           activity_name=original_activity.name)

@activity.route("/delete/<user>/<activity_name>")
def delete(user, activity_name):
    del_activity = Activity.query.filter_by(name=activity_name, creator=user).first()
    past_stats = Timestamp.query.filter_by(activity_id=del_activity.id, actor_id=user).all()
    if del_activity:
        db.session.delete(del_activity)
        for stat in past_stats:
            db.session.delete(stat)
        db.session.commit()
    return redirect(url_for("activity.list", user=user))

def create_plot(user, activity_name):
    activity_id = db.session.query(Activity).filter_by(name=activity_name).first().id
    timestamps = Timestamp.query.filter_by(activity_id=activity_id,actor_id=user).all()
    # create tuple of dates and checkin
    checkins = sorted([timestamp.timestamp for timestamp in timestamps])
    delta = checkins[len(checkins)-1] - checkins[0]
    dates = [checkins[0] + timedelta(days=day) for day in range(delta.days)]
    print("Dates:",dates)
    y_marks = [None] * delta.days
    for index, date in enumerate(dates):
        if date in checkins:
            y_marks[index] = 1
        else:
            y_marks[index] = 0
    fig = BytesIO()
    plt.plot_date(x=dates, y=y_marks, fmt='-')
    plt.savefig(fig)
    plt.clf()
    fig.seek(0)
    return fig


