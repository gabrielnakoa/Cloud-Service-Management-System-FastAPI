# Cloud Service Access Management System built with FastAPI
DEMO RECORDING: https://youtu.be/1fiusH1su9E

# HOW TO RUN:
-------------
1. clone this repository to your local machine
2. Set Up the MySQL Database
- Start Your MySQL Server
- Ensure your MySQL server is running locally.

- A script to create the database and tables may be provided in the repository. If not, manually create the necessary database and tables.
- Here's the database schema for reference:
Table: users
user_id (Primary Key)
username
password
plan

Table: subscription_plan
plan_id (Primary Key)
plan_name
plan_limit
plan_description

Table: services
service_id (Primary Key)
service_name

Table: service_usage
usage_id (Primary Key)
user_id (Foreign Key)
service_id (Foreign Key)
calls_made

Table: service_plan_mapping
plan_id
service_id

3. Set Up Your Virtual Environment
- Create a virtual environment in your project directory
- Activate it

4. Install Dependencies
- Install the required dependencies:
- pip install -r requirements.txt

5. Run the Application
- Start the FastAPI application:
- uvicorn app:main --reload

7. Test the Endpoints using Postman
- Register a New User
URL: /register
Method: POST
Body: Provide username, and password in the JSON body.
- Login and Obtain JWT
URL: /login
Method: POST
Body: Provide username and password to get a JWT token.
- Access a Service
URL: /services/{service_name}
Method: GET
- Change a user's plan as an admin
URL: /admin/change-plan/
Method: PUT
Body: Provide a username and new_plan
- Change a plan as a customer
URL: /subscribe/
Method: PUT
Body: Provide the name of a new plan
- View current plan as a customer
URL: /see-plan/
Method: GET
- View the amount of calls you made as a customer
URL: /usage-statistics/
Method: GET
- Create a plan as an admin
URL: /admin/create-plan/
Method: POST
Body: {
    plan_name: str
    plan_limit: int
    plan_description: str
    plan_services: List[str]
}
- Delete a plan as an admin
URL: /admin/delete-plan/{plan_name}
Method: DELETE
- Make a change to an existing plan as an admin
URL: /admin/update-plan/{old_plan}
Method: PUT
- Create a new service as an admin
URL: /admin/add-service/
Method: POST
- Delete a service as an admin
URL: /admin/delete-service/{service_name}
Method: DELETE
- Make a change to an existing service as an admin
URL: /admin/update-service/{old_service_name}
Method: PUT