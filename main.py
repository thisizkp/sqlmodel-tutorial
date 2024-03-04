from typing import List, Optional

from fastapi import FastAPI
from sqlmodel import Relationship, SQLModel, Field, Session, create_engine, select, col


class HeroTeamLink(SQLModel, table=True):
    # through model for many-to-many relationships
    team_id: Optional[int] = Field(default=None, foreign_key="team.id", primary_key=True)
    hero_id: Optional[int] = Field(default=None, foreign_key="hero.id", primary_key=True)


class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    headquarters: str

    # `Relationship` doesn't represent a column in the database
    #       instead the value is the entire object that is related
    #       team.heroes = will give the list of heroes (Hero instances)
    #
    # `back_populates` - if something changes in this model, it should change that attribute in the other model
    #       refers to - name of the attribute in the other model that will reference the current model
    #       always refers to the current model class you are editing.
    #       ex: in model `Team`, `back_populates` refer to attribute `teams` or similar in other related models
    #
    # What happens if not using `back_populates`?
    #       when dealing with python objects, it will lead to inconsistencies before commit
    #       ex: modifying team.heroes will not modify hero.teams
    #
    # Why do we need a string "Hero" instead of just Hero?
    #       python doesn't know of any class Hero, at the time of creating this class
    #       so a string representation of the class name ("Hero")
    #       but the editor & SQLModel knows that it is referring to a class
    #
    # Why do we need `link_model`
    #       allows us to define Many-to-Many relationships using a through model
    heroes: list["Hero"] = Relationship(back_populates="teams", link_model=HeroTeamLink)

# Data model only, but still allows us to create index
# won't affect this model, but any model that inherits from this model & has `table=True`
class HeroBase(SQLModel):
    # Why use an Index?
    #       use index to improve read performance at the cost of write performance & additional storage
    name: str = Field(index=True)
    secret_name: str

    # Why use Optional?
    #       age is not required when validating data and it has a default value of None.
    #       translates to `NULL` in the database.
    age: Optional[int] = Field(default=None, index=True)


class Hero(HeroBase, table=True):
    # Why setting Optional here?
    #       id will be generated by the database, not by our code.
    #       value of id will be `None` until we save it in the database.
    # Why setting default=None?
    #       if we don't set the default value,
    #       it will always require passing that `None` value while creating a new instance of this class
    # Why doesn't primary key doesn't have index=True?
    #       database always creates an internal index for primary keys automatically
    id: Optional[int] = Field(default=None, primary_key=True)

    # How to define a foreign key?
    #      foreign_key="team.id" tells db that this column is a foreign key to the table team
    #      Optional cause it could be NULL (or None in python)
    # team_id: Optional[int] = Field(default=None, foreign_key="team.id")

    teams: List[Team] = Relationship(back_populates="heroes", link_model=HeroTeamLink)


class HeroCreate(HeroBase):
    pass


class HeroRead(HeroBase):
    id: int


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# configuration that SQLAlchemy passes to the low-level library in charge of communicating to the db
# we need to make sure we don't share the same session in more than one request
# FastAPI each request could be handled by multiple interacting threads, so need to disable it.
connect_args = {"check_same_thread": False}

# have a single engine object for the entire application and reuse it.
# echo=True prints all the SQL statements that are executed.
# engine is responsible for communicating with the database, handling the connections..etc
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)


# if this was not in a separate function,
# it would create database and tables every time we import this module as a side effect
def create_db_and_tables():
    # create the database and all the tables registered in the MetaData object
    # has to be called after the code that creates new model classes inherting from SQLModel
    # the order in which it is called is important. MetaData object should be created first before calling this.
    # MetaData is registered when we create a new model class
    SQLModel.metadata.create_all(engine)


def create_heroes():
    # create a new session for each group of operations with the database that belong together
    # a single session per request will create a new transaction and execute all the SQL code in that transaction
    # ensures that data is saved in a single batch. either all succeed or all fail
    with Session(engine) as session:
        # without Relationship attributes
        # each team has to be added first, committed and then heroes can be added
        # as the heroes need the respective team.ids
        # Relationship attributes helps in not committing multiple times
        # by automatically creating the related records in the database and assigning the ids
        #       team_z_force = Team(name='Z-Force', headquarters="Sister Margaret’s Bar")
        #       team_preventers = Team(name='Preventers', headquarters="Sharp Tower")
        #       session.add(team_z_force)
        #       session.add(team_preventers)
        #       session.commit()

        team_preventers = Team(name='Preventers', headquarters="Sharp Tower")
        team_z_force = Team(name='Z-Force', headquarters="Sister Margaret’s Bar")

        hero_1 = Hero(name="Deadpond", secret_name="Dive Wilson", teams=[team_z_force])
        hero_2 = Hero(name="Spider-Boy", secret_name="Pedro Parqueador", teams=[team_preventers])

        # can also add data on the many side using Relationship attributes
        hero_3 = Hero(name="Black Lion", secret_name="Trevor Challa", age=35)
        hero_4 = Hero(name="Princess Sure-E", secret_name="Sure-E", age=25)
        team_wakanda = Team(name='Wakanda', headquarters="Wakanda", heroes=[hero_3, hero_4])

        # can use list.append: behaves like a list but special list
        # when we modify it, SQLAlchemy keeps track of necessary changes to be done in the database
        hero_5 = Hero(name="Rusty-Man", secret_name="Tommy Sharp", age=48)
        team_wakanda.heroes.append(hero_5)

        # holding in memory all the objects that should be saved in the database later
        session.add(hero_1)
        session.add(hero_2)
        session.add(team_wakanda)

        # on commit, session will use the engine underneath to save all the data
        # by sending the appropriate SQL to the database
        session.commit()

        print("After committing the session")

        # Why is the data empty?
        #       SQLAlchemy doesn't automatically refresh the data from the database
        #       it marks the object as expired as it doesn't have the latest version of data
        #       it has no way of knowing that we want to access the object data
        print("Hero 1:", hero_1)

        # Manual refresh the data by accessing the attribute (fetches from the database)
        print("Hero 1 ID:", hero_1.id)

        # Already has the refreshed data and doesn't refetch as it is not expired
        print("Hero 1 Name:", hero_1.name)

        # Explicitly refresh the data from the database
        session.refresh(hero_2)
        print("Hero 2 Team:", hero_2.team_id)

    # Manually closing the session
    #       once done with the session, close it to release the resources and finish any cleanup
    #       used when manually creating a session instead of using `with`
    # session.close()


def select_heroes():
    with Session(engine) as session:
        # Model attributes vs Instance attributes
        #      Model attributes are special and can be used for expressions
        #      Instance attributes behave like normal python values
        #      ex: hero_1.name == "Deadpond" will result in True or False
        #      ex: Hero.name == "Deadpond" doesn't result in True or False but an expression object
        # When to use expression objects?
        #      `where` clause doesn't support keyword arguments and needs an expression object
        # How to fix comparison with NULL (Optional values)?
        #       SQLModel is aware that comparison only applies for values that are not NULL in the database
        #       use `col` function to tell the editor that class attribute is SQLModel column
        # How to use `offset` & `limit`?
        #       ex: select(Hero).where(col(Hero.age) < 35).offset(2).limit(3)
        # Joins using Where clause
        #       get data from tables hero & team but don't want all possible combinations of hero and team
        #       give me only the ones where hero.team_id == team.id
        #       ex: statement = select(Hero, Team).where(Hero.team_id == Team.id)
        # Joins using Join clause
        #       ex: statement = select(Hero, Team).join(Team, isouter=True)
        #       already knows what the foreign key is, so no need to pass `ON` part
        #       isouter=True to make the JOIN be LEFT OUTER JOIN
        #       select(A,B) tells that we want to select columns from both A and B
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

        # Don't use session.refresh while deleting
        #       session.refresh raises an exception as there's no data in the database
        #       session doesn't care about the object anymore and is not marked as expired
        #       in memory object still remains and can be used
        print("Deleted hero:", hero)

        # confirm if deleted?
        statement = select(Hero).where(Hero.name == "Spider-Boy")
        results = session.exec(statement)
        hero = results.first()

        if hero is None:
            print("There's no hero named Spider-Boy")

app = FastAPI()

# called only on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# response_model to tell FastAPI the schema of the data we want to send back
# response_model also validates all the data that we promised is there and will remove any extra data
@app.post("/heroes", response_model=HeroRead)
def create_hero(hero: HeroCreate):
    with Session(engine) as session:
        # reads data from another object with attributes and
        # creates a new instance of this class (Hero)
        db_hero = Hero.model_validate(hero)
        session.add(hero)
        session.commit()
        session.refresh(hero)
        return hero

@app.get("/heroes", response_model=List[Hero])
def read_heroes():
    with Session(engine) as session:
        heroes = session.exec(select(Hero)).all()
        return heroes

# Why __name__ == "__main__"?
#       code that is executed when called with `python app.py`
#       __name__ is set to main when called from a terminal
#       but not called when another file imports it like `from app import something`
# if __name__ == "__main__":
#    main()
