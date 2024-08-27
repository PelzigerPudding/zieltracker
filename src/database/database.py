''' Module for database connection '''

from flask import g
from pymysql import connect, cursors

from src.util import config_util

def init_db(app):
    ''' Initializes database functionality by calling the close_db function
        after every request. '''
    app.teardown_appcontext(close_db)

def get_db():
    ''' Returns the database connection. If it doesnt exist yet, it is created
    first.
    Returns:
        pymysql.connections.Connection -- The database connection. '''
    if g:
        if "db" not in g:
            db_config = config_util.get("database")
            g.db = connect(host=db_config["hostname"],
                           user=db_config["username"],
                           password=db_config["password"],
                           db=db_config["database"],
                           cursorclass=cursors.DictCursor)
        return g.db

    db_config = config_util.get("database")
    return connect(host=db_config["hostname"],
                   user=db_config["username"],
                   password=db_config["password"],
                   db=db_config["database"],
                   cursorclass=cursors.DictCursor)

def close_db(_=None):
    ''' Closes the database connections, if any exist. This is usually called
        after a request is done. '''
    for key in ("db"):
        db_ = g.pop(key, None)
        if db_ is not None:
            db_.close()


def create_table_if_not_exists():
    ''' Creates tables in the database if they do not already exist. '''
    db = get_db()
    cursor = db.cursor()

    # Score Table
    create_score_table = """
    CREATE TABLE IF NOT EXISTS Score (
        score_id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL
    );
    """

    # Divisions Table
    create_divisions_table = """
    CREATE TABLE IF NOT EXISTS Divisions (
        division_id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL
    );
    """

    # Collaborators Table
    create_collaborators_table = """
    CREATE TABLE IF NOT EXISTS Collaborators (
        collaborator_id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL
    );
    """

    # UpdateHistories Table
    create_update_histories_table = """
    CREATE TABLE IF NOT EXISTS UpdateHistories (
        updateHistory_id INT AUTO_INCREMENT PRIMARY KEY,
        collaborator_id INT,
        division_id INT,
        score_id INT DEFAULT 1,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        criteria TEXT,
        comment TEXT,
        additionalInformation TEXT,
        createdAt DATE DEFAULT CURRENT_DATE NOT NULL,
        lastUpdateID INT DEFAULT NULL,
        FOREIGN KEY (collaborator_id) REFERENCES Collaborators(collaborator_id),
        FOREIGN KEY (division_id) REFERENCES Divisions(division_id),
        FOREIGN KEY (score_id) REFERENCES Score(score_id)
    );
    """

    # Goals Table
    create_goals_table = """
    CREATE TABLE IF NOT EXISTS Goals (
        goal_id INT AUTO_INCREMENT PRIMARY KEY,
        updateHistory_id INT,
        collaborator_id INT,
        createdAt DATE DEFAULT CURRENT_DATE NOT NULL,
        FOREIGN KEY (updateHistory_id) REFERENCES UpdateHistories(updateHistory_id),
        FOREIGN KEY (collaborator_id) REFERENCES Collaborators(collaborator_id)
    );
    """

    try:
        # Create Tables
        cursor.execute(create_score_table)
        cursor.execute(create_divisions_table)
        cursor.execute(create_collaborators_table)
        cursor.execute(create_update_histories_table)
        cursor.execute(create_goals_table)

        db.commit()
    except Exception as e:
        print(f"Error could not create Tables: {e}")
    finally:
        cursor.close()