import jwt, asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional
from sqlalchemy.dialects.mysql import JSON

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login/")

app = FastAPI()

DATABASE_URL = "mysql+pymysql://root:Password1!@localhost/cloud_service_management"

Base = declarative_base()

engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)



# Subscription Plan Model
class SubscriptionPlan(Base):
    __tablename__ = "subscription_plan"
    plan_id = Column(Integer, primary_key=True, index=True)
    plan_name = Column(String(225), nullable=False)
    plan_limit = Column(Integer, nullable=False)
    plan_description = Column(String(225))
    services = relationship(
        "Service",
        secondary="service_plan_mapping",
        back_populates="plans",
        #cascade="all, delete"
    )


# Service Model
class Service(Base):
    __tablename__ = "services"
    service_id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(225), nullable=False)
    service_description = Column(String(225))
    service_endpoint = Column(String(225))
    plans = relationship(
        "SubscriptionPlan",
        secondary="service_plan_mapping",
        back_populates="services",
        #cascade="all, delete"
    )


# Mapping Table
class ServicePlanMapping(Base):
    __tablename__ = "service_plan_mapping"
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.service_id", ondelete="CASCADE"))
    plan_id = Column(Integer, ForeignKey("subscription_plan.plan_id", ondelete="CASCADE"))


# Users Model
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(50), default="customer")
    plan = Column(String(100), default="basic")
    service_usage = relationship(
        "ServiceUsage",
        back_populates="user",
        cascade="all, delete"
    )


# Service Usage Model
class ServiceUsage(Base):
    __tablename__ = "service_usage"

    usage_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.service_id", ondelete="CASCADE"))
    calls_made = Column(Integer, default=0)
    user = relationship("User", back_populates="service_usage")


Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#JWT config
SECRET_KEY = "ABC"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

#access control
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("identity")

        user = db.query(User).filter(User.user_id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")

    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_current_admin_user(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to perform this action.")

    return user




class UserCreate(BaseModel):
    username: str
    password: str
    role: str = None
    plan: str = None

@app.post("/register/")
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(
        username=user.username,
        password=user.password,
        role=user.role if user.role else "customer",
        plan=user.plan if user.plan else "basic"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully", "user_id": new_user.user_id, "role": new_user.role, "plan": new_user.plan}

@app.post("/login/")
async def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()

    if not db_user or db_user.password != user.password:
        raise HTTPException(status_code=400, detail="Invalid username or password")

    access_token = create_access_token({"identity": db_user.user_id})

    return {"message": "Login successful", "access_token": access_token}


#start of user subscription handling

#admin
@app.put("/admin/change-plan/")
async def change_users_plan(
    username: str,
    plan: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    target_user = db.query(User).filter(User.username == username).first()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    target_user.plan = plan
    db.commit()

    user_service_usages = db.query(ServiceUsage).filter(
        ServiceUsage.user_id == target_user.user_id
    ).all()

    for usage in user_service_usages:
        usage.calls_made = 0

    db.commit()

    return JSONResponse(content={"message": f"{username}'s subscription plan has been updated to {plan} by admin {current_admin.user_id}"})

#customer

import logging

logging.basicConfig(level=logging.INFO)

@app.put("/subscribe/")
async def change_plan(
    new_plan: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        plan_exists = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_name == new_plan).first()

        if not plan_exists:
            raise HTTPException(status_code=400, detail=f"Plan '{new_plan}' does not exist.")

        # Change the user's plan
        current_user.plan = new_plan
        print(f"Received new_plan: {new_plan} (type: {type(new_plan)})")
        db.commit()

        # Reset service usage calls
        user_service_usages = db.query(ServiceUsage).filter(
            ServiceUsage.user_id == current_user.user_id
        ).all()

        for usage in user_service_usages:
            usage.calls_made = 0

        db.commit()

        return {"message": f"Subscription plan has been changed to {new_plan} for user: {current_user.username}"}

    except Exception as e:
        logging.error(f"Error subscribing to a plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

#customer
@app.get("/see-plan/")
async def view_current_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_name == current_user.plan).first()

    return {
        "plan_name": plan.plan_name,
        "plan_limit": plan.plan_limit
    }

#customer
@app.get("/usage-statistics/")
async def view_usage_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.user_id
    user_plan = current_user.plan

    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_name == user_plan).first()

    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {user_plan} does not exist")

    associated_services = plan.services

    service_data = (
        db.query(ServiceUsage.service_id, func.sum(ServiceUsage.calls_made).label("total_calls"))
        .filter(ServiceUsage.user_id == user_id)
        .group_by(ServiceUsage.service_id)
        .all()
    )

    calls_dict = {data.service_id: data.total_calls for data in service_data}

    usage_data = []
    total_calls = 0

    for service in associated_services:
        calls_made = calls_dict.get(service.service_id, 0)
        total_calls += calls_made

        usage_data.append({
            "service": service.service_name,
            "calls_made": calls_made
        })

    return {
        "usage_data": usage_data,
        "total_calls": total_calls
    }


#end of user subscription handling


#start of subscription plan management


class PlanCreate(BaseModel):
    name: str
    limit: int
    description: str
    services: List[str]

#admin
@app.post("/admin/create-plan/")
async def add_new_plan(
    new_plan: PlanCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    existing_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_name == new_plan.name).first()
    if existing_plan:
        raise HTTPException(status_code=400, detail="Plan already exists")

    existing_services = db.query(Service).filter(Service.service_name.in_(new_plan.services)).all()
    if len(existing_services) != len(new_plan.services):
        raise HTTPException(status_code=400, detail="One or more service names are invalid.")

    created_plan = SubscriptionPlan(
        plan_name=new_plan.name,
        plan_description=new_plan.description,
        plan_limit=new_plan.limit
    )
    db.add(created_plan)
    db.commit()
    db.refresh(created_plan)

    for service in existing_services:
        mapping = ServicePlanMapping(plan_id=created_plan.plan_id, service_id=service.service_id)
        db.add(mapping)
    
    db.commit()

    service_names = [service.service_name for service in existing_services]
    return {
        "message": f"Plan '{created_plan.plan_name}' created successfully.",
        "services": service_names
    }

#admin
@app.delete("/admin/delete-plan/{plan_name}")
async def delete_plan(
    plan_name: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user) 
):
    existing_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_name == plan_name).first()
    if not existing_plan:
        raise HTTPException(status_code=404, detail=f"{plan_name} plan does not exist")
    
    db.delete(existing_plan)
    db.commit()

    return {"message": f"{plan_name} plan deleted by admin {current_admin.user_id}"}

#admin
@app.put("/admin/update-plan/{old_plan}")
async def update_plan(
    old_plan: str,
    updated_plan: PlanCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)   
):
    existing_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_name == old_plan).first()

    if not existing_plan:
        raise HTTPException(status_code=404, detail=f"{old_plan} plan does not exist")

    existing_plan.plan_name = updated_plan.name
    existing_plan.plan_limit = updated_plan.limit
    existing_plan.plan_description = updated_plan.description

    #clear existing service for old plan
    db.query(ServicePlanMapping).filter(ServicePlanMapping.plan_id == existing_plan.plan_id).delete()

    #new services to updated_plan
    existing_services = db.query(Service).filter(Service.service_name.in_(updated_plan.services)).all()

    if len(existing_services) != len(updated_plan.services):
        raise HTTPException(status_code=400, detail="One or more service names are invalid.")

    for service in existing_services:
        mapping = ServicePlanMapping(plan_id=existing_plan.plan_id, service_id=service.service_id)
        db.add(mapping)

    db.commit()

    return {"message": f"{updated_plan.name} plan updated successfully by admin {current_admin.user_id}"}

#end of subscription plan management


#start of service management


class ServiceCreate(BaseModel):
    name: str
    endpoint: str
    description: Optional[str]

#admin
@app.post("/admin/add-service/")
async def add_new_service(
    new_service: ServiceCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    exists = db.query(Service).filter(Service.service_name == new_service.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Service already exists")

    service = Service(
        service_name=new_service.name,
        service_endpoint=new_service.endpoint,
        service_description=new_service.description,
    )

    db.add(service)
    db.commit()
    db.refresh(service)

    return {"message": f"{new_service.name} created by admin {current_admin.user_id}"}

#admin
@app.delete("/admin/delete-service/{service_name}")
async def delete_service(
    service_name: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    existing_service = db.query(Service).filter(Service.service_name == service_name).first()
    if not existing_service:
        raise HTTPException(status_code=404, detail=f"{service_name} does not exist")
    
    db.delete(existing_service)
    db.commit()

    return {"message": f"{service_name} deleted by admin {current_admin.user_id}"}

#admin
@app.put("/admin/update-service/{old_service_name}")
async def update_service(
    old_service_name: str,
    new_service: ServiceCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    existing_service = db.query(Service).filter(Service.service_name == new_service.name).first()
    if existing_service:
        raise HTTPException(status_code=400, detail=f"{new_service.name} already exists")

    old_service = db.query(Service).filter(Service.service_name == old_service_name).first()
    if not old_service:
        raise HTTPException(status_code=404, detail=f"{old_service_name} does not exist")

    old_service.service_name=new_service.name
    old_service.service_endpoint=new_service.endpoint
    old_service.service_description=new_service.description
    db.commit()
    db.refresh(old_service)

    return {"message": f"{new_service.name} updated by admin {current_admin.user_id}"}


#just in case
@app.post("/admin/associate-service/{service_name}")
async def associate_service_to_plan(
    service_name: str,
    plan_names: List[str],
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    service = db.query(Service).filter(Service.service_name == service_name).first()
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' does not exist")

    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.plan_name.in_(plan_names)).all()

    if len(plans) != len(plan_names):
        missing_plans = set(plan_names) - {plan.plan_name for plan in plans}
        raise HTTPException(
            status_code=404,
            detail=f"The following plans do not exist: {', '.join(missing_plans)}"
        )

    for plan in plans:
        if plan not in service.plans:
            service.plans.append(plan)

    db.commit()

    return {
        "message": f"Service '{service_name}' successfully associated with plans: {plan_names}"
    }


#end of service management

# storage
# database
# compute
# email
# notification
# ai process
@app.get("/services/{service_name}")
async def access_service(
    service_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = db.query(Service).filter(Service.service_name == service_name).first()

    if not service:
        raise HTTPException(status_code=404, detail=f"{service_name} service not found.")

    service_id = service.service_id

    subscription_plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.plan_name == current_user.plan
    ).first()

    if not subscription_plan:
        raise HTTPException(status_code=404, detail="User's subscription plan not found.")

    plan_id = subscription_plan.plan_id

    plan_service = db.query(ServicePlanMapping).filter(
        ServicePlanMapping.plan_id == plan_id,
        ServicePlanMapping.service_id == service_id
    ).first()

    if not plan_service:
        raise HTTPException(status_code=403, detail=f"{service_name} is not included in the user's subscription plan.")

    service_usage = db.query(ServiceUsage).filter(
        ServiceUsage.user_id == current_user.user_id,
        ServiceUsage.service_id == service_id
    ).first()

    if not service_usage:
        service_usage = ServiceUsage(user_id=current_user.user_id, service_id=service_id, calls_made=1)
        db.add(service_usage)
        db.commit()

        return {"message": f"{service_name} accessed successfully, call count initialized to 1."}

    subscription_plan_limit = subscription_plan.plan_limit

    if service_usage.calls_made >= subscription_plan_limit:
        raise HTTPException(status_code=403, detail="Total call limit reached for this service.")

    service_usage.calls_made += 1
    db.commit()

    return {"message": f"{service_name} accessed successfully, calls made: {service_usage.calls_made}"}



async def reset_calls(db: Session):
    user_service_usages = db.query(ServiceUsage).all()

    for usage in user_service_usages:
        usage.calls_made = 0

    db.commit()

@app.on_event("startup")
async def startup_event():
    from asyncio import create_task
    from datetime import datetime, timedelta

    async def reset_calls_periodically():
        while True:
            await asyncio.sleep(86400) #24 hours
            db = get_db()
            await reset_calls(db)

    create_task(reset_calls_periodically())