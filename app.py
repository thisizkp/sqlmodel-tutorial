from typing import Optional

from sqlmodel import Relationship, SQLModel, Field, Session, create_engine, select, col


class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    headquarters: str

    # don't represent a column in the database
    # value is the actual entire object that is related
    # team.heroes = will give the list of heroes (Hero instances)
    # back_populates = if something changes in this model,
    # it should change that attribute in the other model
    # name of the attribute in the other model that will reference the current model
    # trick: always refers to the current model class you are editing.
    # not using back_populates will lead to inconsistencies before commit when dealing with python objects
    # python doesn't know of any class Hero, so a string "Hero". But the editor & SQLModel is aware of that
    heroes: list["Hero"] = Relationship(back_populates="team")


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

    # could be NULL (or None in python)
    # foreign_key="team.id" tells db that this column is a foreign key to the table team
    team_id: Optional[int] = Field(default=None, foreign_key="team.id")
    team: Optional[Team] = Relationship(back_populates="heroes")


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
    # create a new session for each group of operations with the database that belong together
    # a single session per request
    # will create a new transaction and execute all the SQL code in that transaction
    # ensures that data is saved in a single batch. either all succeed or all fail
    with Session(engine) as session:
        team_preventers = Team(name='Preventers', headquarters="Sharp Tower")
        team_z_force = Team(name='Z-Force', headquarters="Sister Margaret’s Bar")į
        # Relationship attributes helps in not committing twice
        #session.add(team_preventers)
        #session.add(team_z_force)
        #session.commit()

        # if not using relationship attributes, have to manually add the foreign key id
        # with relationships attributes, it can automatically infer that
        # here instead of passing the team_id, we are passing the entire team object
        # teams will be automatically created in the database and the id will be automatically assigned
        hero_1 = Hero(name="Deadpond", secret_name="Dive Wilson", team=team_z_force)
        hero_2 = Hero(name="Spider-Boy", secret_name="Pedro Parqueador", team=team_preventers)

        # we could also create heroes first and then teams later when using Relationship attributes
        hero_3 = Hero(name="Black Lion", secret_name="Trevor Challa", age=35)
        hero_4 = Hero(name="Princess Sure-E", secret_name="Sure-E", age=25)
        team_wakanda = Team(name='Wakanda', headquarters="Wakanda", heroes=[hero_3, hero_4])

        # can also add data on the many side
        hero_5 = Hero(name="Rusty-Man", secret_name="Tommy Sharp", age=48)
        # behaves like a list but special list,
        # when we modify it, SQLAlchemy keeps track of necessary changes to be done in the database
        team_wakanda.heroes.append(hero_5)

        # does automatic refresh as we are referring to team_z_force.id
        # hero_1 = Hero(name="Deadpond", secret_name="Dive Wilson", team_id=team_z_force.id)
        # hero_2 = Hero(name="Spider-Boy", secret_name="Pedro Parqueador", team_id=team_preventers.id)
        # hero_3 = Hero(name="Rusty-Man", secret_name="Tommy Sharp", age=48)
        # hero_4 = Hero(name="Tarantula", secret_name="Natalia Roman-on", age=32)
        # hero_5 = Hero(name="Black Lion", secret_name="Trevor Challa", age=35)
        # hero_6 = Hero(name="Dr. Weird", secret_name="Steve Weird", age=36)
        # hero_7 = Hero(name="Captain North America", secret_name="Esteban Rogelios", age=93)

        # holding in memory all the objects that should be saved in the database later
        session.add(hero_1)
        session.add(hero_2)
        session.add(team_wakanda)
        # session.add(hero_3)
        # session.add(hero_4)
        # session.add(hero_5)
        # session.add(hero_6)
        # session.add(hero_7)


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
        session.refresh(hero_2)
        print("Hero 2 Team:", hero_2.team_id)

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
        #heroes = session.exec(select(Hero).where(col(Hero.age) < 35).offset(2).limit(3)).all()
        #print(heroes)

        # get data from tables hero & team.
        # don't want all possible combinations of hero and team
        # but give me only the ones where hero.team_id == team.id
        # statement = select(Hero, Team).where(Hero.team_id == Team.id)

        # already knows what the foreign key is, so no need to pass `ON` part
        # isouter=True to make the JOIN be LEFT OUTER JOIN
        # select(A,B) tells that we want to select columns from both A and B
        statement = select(Hero, Team).join(Team, isouter=True)
        results = session.exec(statement)
        for hero, team in results:
            print("Hero:", hero, "Team:", team)


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


def delete_heroes():
    with Session(engine) as session:
        statement = select(Hero).where(Hero.name == "Spider-Boy")
        results = session.exec(statement)
        hero = results.one()
        print("Hero to delete:", hero)

        session.delete(hero)
        session.commit()

        # session.refresh raises an exception as there's no data in the database
        # object is not connected to the session, so not marked as "expired"
        # session doesn't care about the object anymore, so object is still present in memory
        print("Deleted hero:", hero)

        # confirm if deleted?
        statement = select(Hero).where(Hero.name == "Spider-Boy")
        results = session.exec(statement)
        hero = results.first()

        if hero is None:
            print("There's no hero named Spider-Boy")


def main():
    create_db_and_tables()
    create_heroes()
    #select_heroes()
    #update_heroes()
    #delete_heroes()

# purpose of __name__ == "__main__"
# is to have some code that is executed when called with `python app.py`
# but no called when another file imports it like `from app import something`
if __name__ == "__main__":
    main()
