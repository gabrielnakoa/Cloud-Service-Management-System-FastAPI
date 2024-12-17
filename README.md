# Cloud Service Access Management System built with FastAPI
DEMO RECORDING: https://youtu.be/1fiusH1su9E
- Gabriel Bulosan
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
/register
Register a new user.

/login
Log in and obtain a JWT token.

/services/{service_name}
Access a service.

/admin/change-plan/
Change a user's plan as an admin.

/subscribe/
Change a plan as a customer.

/see-plan/
View the current plan as a customer.

/usage-statistics/
View the amount of calls you made as a customer.

/admin/create-plan/
Create a plan as an admin.

/admin/delete-plan/{plan_name}
Delete a plan as an admin.

/admin/update-plan/{old_plan}
Make changes to an existing plan as an admin.

/admin/add-service/
Create a new service as an admin.

/admin/delete-service/{service_name}
Delete a service as an admin.

/admin/update-service/{old_service_name}
Make changes to an existing service as an admin.
