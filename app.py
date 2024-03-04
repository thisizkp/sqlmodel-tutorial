from typing import Optional

from sqlmodel import SQLModel, Field, Session, create_engine, select, col

class Hero(SQLModel, table=True):
    # id will be generated by the database, not by our code.
    # value of id will be `None` until we save it in the database.
    # if we don't set the default value,
    # it will always require passing that `None` value while doing data validation.
    id: Optional[int] = Field(default=None, primary_key=True)

    # database always creates an internal index for primary keys automatically
    # use index to improve reading performance at the cost of writing performance & additional storage
    name: str = Field(index=True)
    secret_name: str

    # age is not required when validating data and it has a default value of None.
    # translates to `NULL` in the database.
    age: Optional[int] = None


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# have a single engine object for the entire application and reuse it.
# echo=True prints all the SQL statements that are executed.
# engine is responsible for communicating with the database, handling the connections..etc
engine = create_engine(sqlite_url, echo=True)


# if this was not in a separate function,
# it would create database and tables every time we import this module as a side effect
def create_db_and_tables():
    # create the database and all the tables registered in the MetaData object
    # has to be called after the code that creates new model classes inherting from SQLModel
    SQLModel.metadata.create_all(engine)


def create_heroes():
    hero_1 = Hero(name="Deadpond", secret_name="Dive Wilson")
    hero_2 = Hero(name="Spider-Boy", secret_name="Pedro Parqueador")
    hero_3 = Hero(name="Rusty-Man", secret_name="Tommy Sharp", age=48)
    hero_4 = Hero(name="Tarantula", secret_name="Natalia Roman-on", age=32)
    hero_5 = Hero(name="Black Lion", secret_name="Trevor Challa", age=35)
    hero_6 = Hero(name="Dr. Weird", secret_name="Steve Weird", age=36)
    hero_7 = Hero(name="Captain North America", secret_name="Esteban Rogelios", age=93)

    # create a new session for each group of operations with the database that belong together
    # a single session per request
    # will create a new transaction and execute all the SQL code in that transaction
    # ensures that data is saved in a single batch. either all succeed or all fail
    with Session(engine) as session:
        # holding in memory all the objects that should be saved in the database later
        session.add(hero_1)
        session.add(hero_2)
        session.add(hero_3)
        session.add(hero_4)
        session.add(hero_5)
        session.add(hero_6)
        session.add(hero_7)


        # on commit, session will use the engine underneath to save all the data
        # by sending the appropriate SQL to the database
        session.commit()

        print("After committing the session")
        # will print empty
        # because SQLAlchemy internally marks the object as expired as it doesn't have the latest version of data
        # SQLAlchemy has no way of knowing that we want to access the object data
        print("Hero 1:", hero_1)

        # by accessing the attribute, refresh the data from the database (Go to the database)
        print("Hero 1 ID:", hero_1.id)

        # session already refreshed the data and knows they are not expired (no commits in between)
        # so doesn't have to go to the database for names
        print("Hero 1 Name:", hero_1.name)

        # explicitly refresh the data from the database
        # session.refresh(hero_1)

    # once done with the session, close it to release the resources and finish any cleanup
    # used when manually creating a session instead of using `with`
    # session.close()


def select_heroes():
    with Session(engine) as session:
        # SQLModel session.exec is built on top of SQLAlchemy session.execute
        # Hero.name == "Deadpond" doesn't result in True or False but
        # an expression object that can passed to `where` clause
        # Model class attributes are special and can be used for expressions
        # Instance attributes behave like normal python values
        # ex: hero_1.name == "Deadpond" will result in True or False
        # keyword arguments in `where` where(name == "KP") are not supported
        # during execution of the program, special class attributes know that
        # comparison only applies for values that are not NULL in the database
        # but the editor doesn't know that, to fix that, use `col` function
        # `col` function tells editor that class attribute is SQLModel column
        # instead of instance with a value
        heroes = session.exec(select(Hero).where(col(Hero.age) < 35).offset(2).limit(3)).all()
        print(heroes)


def update_heroes():
    with Session(engine) as session:
        statement = select(Hero).where(Hero.name == "Spider-Boy")
        results = session.exec(statement)
        # check if there is a single result
        hero = results.one()
        print("Hero:", hero)

        hero.age = 16
        session.add(hero)
        session.commit()
        session.refresh(hero)
        print("Updated hero:", hero)


def main():
    create_db_and_tables()
    create_heroes()
    update_heroes()

# purpose of __name__ == "__main__"
# is to have some code that is executed when called with `python app.py`
# but no called when another file imports it like `from app import something`
if __name__ == "__main__":
    main()
