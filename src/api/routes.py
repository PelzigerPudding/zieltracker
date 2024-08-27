''' script for the routes of the web service '''

# pylint: disable=unused-variable

from flask import render_template, request

from src.database.database import get_db
from src.util import config_util
from flask import render_template, request, redirect, url_for
from flask import Flask, render_template, request, jsonify
import datetime


def init_routes(app):
    ''' init the routes for the web service '''

    # Main View
    @app.route('/', methods= ['GET'])
    def index():
        with get_db().cursor() as cursor:
            return render_template("index.html.j2")

    def build_chain(data, start_id):
        """
        Rekursiv eine Kette von UpdateHistories basierend auf lastUpdateID erstellen.
        """
        chain = []
        current_id = start_id

        while current_id is not None:
            item = next((d for d in data if d['updateHistory_id'] == current_id), None)

            if item:
                chain.append(item)
                current_id = item['lastUpdateID']
            else:
                break

        return chain

    @app.route('/goals_chart_data')
    def goals_chart_data():
        db = get_db()
        cursor = db.cursor()

        # I show the current Month on the graph
        now = datetime.datetime.now()
        start_date = now.replace(day=1)
        end_date = (now.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

        # Get the Goals
        cursor.execute("""
            SELECT 
                u.updateHistory_id,
                u.lastUpdateID,
                u.createdAt,
                s.name AS score_name,
                COUNT(*) AS count
            FROM 
                UpdateHistories u
            JOIN 
                Score s ON u.score_id = s.score_id
            WHERE 
                u.createdAt BETWEEN %s AND %s
            GROUP BY 
                u.updateHistory_id, u.lastUpdateID, u.createdAt, s.name
            ORDER BY 
                u.createdAt
        """, (start_date, end_date))

        data = cursor.fetchall()

        chains = []
        used_ids = set()

        for item in data:
            if item['updateHistory_id'] not in used_ids:
                chain = build_chain(data, item['updateHistory_id'])
                chains.append(chain)
                used_ids.update(chain[i]['updateHistory_id'] for i in range(len(chain)))

        # Create the axes of the Graph
        dates = [start_date + datetime.timedelta(days=x) for x in range((end_date - start_date).days)]
        labels = [date.strftime('%Y-%m-%d') for date in dates]

        datasets = {}
        for chain in chains:
            goal_id = chain[0]['updateHistory_id']
            dataset = {
                'label': f'Goal {goal_id}',
                'data': [0] * len(labels),
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'borderColor': 'rgba(75, 192, 192, 1)',
                'borderWidth': 1
            }

            for item in chain:
                createdAt = item['createdAt'].strftime('%Y-%m-%d')
                if createdAt in labels:
                    idx = labels.index(createdAt)
                    dataset['data'][idx] += item['count']

            datasets[f'goal_{goal_id}'] = dataset

        chart_data = {
            'labels': labels,
            'datasets': list(datasets.values())
        }

        return jsonify(chart_data)

    # Create new Goal view
    @app.route('/create_goal', methods=['GET', 'POST'])
    def create_goal():
        db = get_db()
        cursor = db.cursor()

        # Get Divisions Data
        cursor.execute("SELECT division_id, name FROM Divisions")
        divisions = cursor.fetchall()

        # Get Collaborators Data
        cursor.execute("SELECT collaborator_id, name FROM Collaborators")
        collaborators = cursor.fetchall()

        # Sent Goal Data
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            criteria = request.form.get('criteria')
            comment = request.form.get('comment')
            additional_information = request.form.get('additionalInformation')
            division_id = request.form.get('division_id')
            collaborator_id = request.form.get('collaborator_id')

            # Insert Into UpdateHistories
            cursor.execute("""
                INSERT INTO UpdateHistories (title, description, criteria, comment, additionalInformation, division_id, collaborator_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (title, description, criteria, comment, additional_information, division_id, collaborator_id))

            updateHistory_id = cursor.lastrowid

            # Insert Into Goals
            cursor.execute("""
                INSERT INTO Goals (updateHistory_id, collaborator_id, createdAt)
                VALUES (%s, %s, CURRENT_DATE)
            """, (updateHistory_id, collaborator_id))
            db.commit()

            return redirect(url_for('index'))

        return render_template('pages/create_goal.html.j2', divisions=divisions, collaborators=collaborators)

    # Delete the current Goal
    @app.route('/delete_goal')
    def delete_goal():
        return render_template('index.html.j2')

    # Show all Goals view
    @app.route('/goal_overview', methods=['GET'])
    def goal_overview():
        db = get_db()
        cursor = db.cursor()

        # Get the Division, Collaborator and Score for the Dropdowns
        cursor.execute("SELECT division_id, name FROM Divisions")
        divisions = cursor.fetchall()

        cursor.execute("SELECT collaborator_id, name FROM Collaborators")
        collaborators = cursor.fetchall()

        cursor.execute("SELECT score_id, name FROM Score")
        scores = cursor.fetchall()

        division_id = request.args.get('division_id')
        collaborator_id = request.args.get('collaborator_id')
        score_id = request.args.get('score_id')
        description = request.args.get('description', '')
        criteria = request.args.get('criteria', '')
        comment = request.args.get('comment', '')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Basis-Query which gets updated with the current filter
        query = """
            SELECT 
                g.goal_id, 
                u.title, 
                u.description, 
                u.criteria, 
                u.comment, 
                u.additionalInformation,
                u.updateHistory_id,
                u.createdAt AS update_createdAt,
                d.name AS division,
                c.name AS collaborator,
                s.name AS score
            FROM 
                Goals g
            LEFT JOIN 
                UpdateHistories u ON g.updateHistory_id = u.updateHistory_id
            LEFT JOIN 
                Divisions d ON u.division_id = d.division_id
            LEFT JOIN 
                Collaborators c ON u.collaborator_id = c.collaborator_id
            LEFT JOIN 
                Score s ON u.score_id = s.score_id
            WHERE 1=1
        """

        # use filter
        params = []
        if division_id:
            query += " AND u.division_id = %s"
            params.append(division_id)
        if collaborator_id:
            query += " AND u.collaborator_id = %s"
            params.append(collaborator_id)
        if score_id:
            query += " AND u.score_id = %s"
            params.append(score_id)
        if description:
            query += " AND u.description LIKE %s"
            params.append(f"%{description}%")
        if criteria:
            query += " AND u.criteria LIKE %s"
            params.append(f"%{criteria}%")
        if comment:
            query += " AND u.comment LIKE %s"
            params.append(f"%{comment}%")
        if start_date:
            query += " AND u.createdAt >= %s"
            params.append(start_date)
        if end_date:
            query += " AND u.createdAt <= %s"
            params.append(end_date)

        # start the request
        cursor.execute(query, params)
        goals = cursor.fetchall()

        return render_template('pages/goal_overview.html.j2', goals=goals, divisions=divisions,
                               collaborators=collaborators, scores=scores)

    # Show edit goal view
    @app.route('/edit_goal/<int:goal_id>', methods=['GET', 'POST'])
    def edit_goal(goal_id):
        conn = get_db()
        cursor = conn.cursor()

        # Get the Division, Collaborator and Score for the Dropdowns
        cursor.execute("SELECT * FROM Divisions")
        divisions = cursor.fetchall()

        cursor.execute("SELECT * FROM Collaborators")
        collaborators = cursor.fetchall()

        cursor.execute("SELECT * FROM Score")
        scores = cursor.fetchall()

        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            criteria = request.form['criteria']
            comment = request.form['comment']
            additionalInformation = request.form['additionalInformation']
            division_id = request.form['division_id']
            collaborator_id = request.form['collaborator_id']
            score_id = request.form['score_id']

            cursor.execute("SELECT updateHistory_id FROM Goals WHERE goal_id = %s", (goal_id,))
            current_update_history_id = cursor.fetchone()['updateHistory_id']

            # Create a new entry in the Updates
            cursor.execute("""
                INSERT INTO UpdateHistories (collaborator_id, division_id, score_id, title, description, criteria, comment, additionalInformation, createdAt, lastUpdateID)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_DATE, %s)
            """, (collaborator_id, division_id, score_id, title, description, criteria, comment, additionalInformation,
                  current_update_history_id))
            conn.commit()

            new_update_history_id = cursor.lastrowid

            # update Goal
            cursor.execute("""
                UPDATE Goals 
                SET updateHistory_id=%s
                WHERE goal_id=%s
            """, (new_update_history_id, goal_id))
            conn.commit()
            conn.close()

            return redirect(url_for('goal_overview'))

        cursor.execute("""
            SELECT g.*, u.*
            FROM Goals g
            JOIN UpdateHistories u ON g.updateHistory_id = u.updateHistory_id
            WHERE g.goal_id = %s
        """, (goal_id,))
        goal = cursor.fetchone()

        conn.close()

        return render_template('pages/edit_goal.html.j2', goal=goal, divisions=divisions, collaborators=collaborators,
                               scores=scores)

    @app.route('/goalHistory')
    def seite4():
        return render_template('pages/goalHistory.html.j2')