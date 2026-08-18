from datetime import datetime, timezone
from enum import Enum
from typing import Optional


from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

DATABASE_URL = "sqlite:///./warehouse.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

class OrderStatus(str, Enum):
    CREATED = "Created"
    ALLOCATED = "Allocated"
    PICKING = "Picking"
    PACKED = "Packed"
    QUALITY_CHECK = "Quality Check"
    DISPATCHED = "Dispatched"
    CANCELLED = "Cancelled"
    PARTIAL = "Partial"

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    location = Column(String, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    reserved = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, nullable=False, default=10)
    reorder_qty = Column(Integer, nullable=False, default=20)
    damaged = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, default=True)

    @property
    def available(self):
        return max(self.stock - self.reserved - self.damaged, 0)

class CustomerOrder(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    customer = Column(String, nullable=False)
    priority = Column(Integer, nullable=False, default=3)
    status = Column(String, nullable=False, default=OrderStatus.CREATED.value)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_items = Column(Integer, default=0)
    allocated_items = Column(Integer, default=0)
    notes = Column(String, default="")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    allocated = Column(Integer, default=0)
    order = relationship("CustomerOrder", back_populates="items")
    product = relationship("Product")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    task_type = Column(String, nullable=False)
    status = Column(String, default="Pending")
    assigned_to = Column(String, default="Unassigned")
    priority = Column(Integer, default=3)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ExceptionLog(Base):
    __tablename__ = "exceptions"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    exception_type = Column(String, nullable=False)
    message = Column(String, nullable=False)
    decision = Column(String, default="Review")
    resolution = Column(String, default="Open")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Warehouse Operations API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ProductCreate(BaseModel):
    sku: str
    name: str
    category: str
    location: str
    stock: int = Field(ge=0)
    reorder_level: int = Field(ge=0)
    reorder_qty: int = Field(ge=1)

class OrderItemCreate(BaseModel):
    sku: str
    quantity: int = Field(gt=0)

class OrderCreate(BaseModel):
    customer: str
    priority: int = Field(default=3, ge=1, le=5)
    items: list[OrderItemCreate]
    notes: str = ""

class ExceptionCreate(BaseModel):
    order_id: Optional[int] = None
    product_id: Optional[int] = None
    exception_type: str
    message: str
    decision: str
    resolution: str

class DamageCreate(BaseModel):
    quantity: int = Field(gt=0)
    reason: str = "Damaged during handling"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def product_dict(p: Product):
    return {
        "id": p.id, "sku": p.sku, "name": p.name, "category": p.category,
        "location": p.location, "stock": p.stock, "reserved": p.reserved,
        "available": p.available, "reorder_level": p.reorder_level,
        "reorder_qty": p.reorder_qty, "damaged": p.damaged, "low_stock": p.available <= p.reorder_level,
        "out_of_stock": p.available == 0,
    }

def seed(db: Session):
    if db.query(Product).count() > 0:
        return
    products = [
        Product(sku="SKU-1001", name="Wireless Mouse", category="Accessories", location="A-01-01", stock=48, reorder_level=15, reorder_qty=40),
        Product(sku="SKU-1002", name="Mechanical Keyboard", category="Accessories", location="A-01-02", stock=24, reorder_level=10, reorder_qty=25),
        Product(sku="SKU-1003", name="27-inch Monitor", category="Displays", location="B-02-01", stock=11, reorder_level=8, reorder_qty=15),
        Product(sku="SKU-1004", name="USB-C Hub", category="Accessories", location="A-02-03", stock=6, reorder_level=10, reorder_qty=30),
        Product(sku="SKU-1005", name="Laptop Stand", category="Office", location="C-01-02", stock=31, reorder_level=12, reorder_qty=20),
        Product(sku="SKU-1006", name="Noise Cancelling Headphones", category="Audio", location="C-02-01", stock=3, reorder_level=8, reorder_qty=20),
        Product(sku="SKU-1007", name="Webcam", category="Accessories", location="A-03-01", stock=16, reorder_level=6, reorder_qty=20),
        Product(sku="SKU-1008", name="Portable SSD 1TB", category="Storage", location="B-01-02", stock=20, reorder_level=8, reorder_qty=15),
    ]
    db.add_all(products)
    db.commit()
    orders = [
        CustomerOrder(customer="Acme Retail", priority=5, status=OrderStatus.CREATED.value, notes="VIP / same-day shipment"),
        CustomerOrder(customer="Nova Systems", priority=4, status=OrderStatus.CREATED.value, notes="B2B priority"),
        CustomerOrder(customer="City Office", priority=2, status=OrderStatus.CREATED.value, notes="Standard delivery"),
    ]
    db.add_all(orders); db.commit()
    sku_to_id = {p.sku: p.id for p in db.query(Product).all()}
    sample_items = [
        [("SKU-1001", 10), ("SKU-1004", 5)],
        [("SKU-1003", 2), ("SKU-1008", 3)],
        [("SKU-1005", 4), ("SKU-1007", 2)],
    ]
    for order, items in zip(orders, sample_items):
        for sku, qty in items:
            db.add(OrderItem(order_id=order.id, product_id=sku_to_id[sku], quantity=qty))
        order.total_items = sum(q for _, q in items)
    db.commit()

@app.on_event("startup")
def startup():
    db = SessionLocal(); seed(db); db.close()

@app.get("/api/health")
def health():
    return {"status": "ok", "warehouse": "WH-01", "name": "Main Fulfillment Center"}

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    orders = db.query(CustomerOrder).all()
    open_orders = [o for o in orders if o.status not in [OrderStatus.DISPATCHED.value, OrderStatus.CANCELLED.value]]
    low = [p for p in products if p.available <= p.reorder_level and p.available > 0]
    out = [p for p in products if p.available == 0]
    pick = db.query(Task).filter(Task.task_type == "Picking", Task.status != "Completed").count()
    exceptions = db.query(ExceptionLog).filter(ExceptionLog.resolution == "Open").count()
    return {
        "warehouse": {"code": "WH-01", "name": "Main Fulfillment Center", "zones": 3},
        "products": len(products), "open_orders": len(open_orders), "low_stock": len(low),
        "out_of_stock": len(out), "picking_tasks": pick, "open_exceptions": exceptions,
        "inventory_units": sum(p.stock for p in products),
        "available_units": sum(p.available for p in products),
        "fulfillment_rate": round((len([o for o in orders if o.status == OrderStatus.DISPATCHED.value]) / max(len(orders), 1)) * 100, 1),
        "bottlenecks": [
            {"area": "Picking", "score": min(100, pick * 12 + 28), "reason": "Open picking tasks"},
            {"area": "Inventory", "score": min(100, (len(low) + len(out)) * 15), "reason": "Low / unavailable SKUs"},
            {"area": "Exceptions", "score": min(100, exceptions * 18), "reason": "Unresolved issues"},
        ]
    }

@app.get("/api/products")
def products(db: Session = Depends(get_db)):
    return [product_dict(p) for p in db.query(Product).order_by(Product.id).all()]

@app.post("/api/products")
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    if db.query(Product).filter(Product.sku == payload.sku).first():
        raise HTTPException(409, "SKU already exists")
    p = Product(**payload.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    return product_dict(p)

@app.post("/api/products/{product_id}/damage")
def damage_product(product_id: int, payload: DamageCreate, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p: raise HTTPException(404, "Product not found")
    p.damaged += payload.quantity
    if p.damaged > p.stock:
        p.damaged = p.stock
    db.add(ExceptionLog(product_id=p.id, exception_type="Damaged Item", message=payload.reason, decision="Remove from allocatable stock", resolution="Resolved"))
    db.commit()
    return product_dict(p)

@app.get("/api/orders")
def get_orders(db: Session = Depends(get_db)):
    result = []
    for o in db.query(CustomerOrder).order_by(CustomerOrder.priority.desc(), CustomerOrder.created_at.asc()).all():
        result.append({
            "id": o.id, "customer": o.customer, "priority": o.priority, "status": o.status,
            "created_at": o.created_at.isoformat(), "total_items": o.total_items, "allocated_items": o.allocated_items,
            "notes": o.notes,
            "items": [{"sku": i.product.sku, "name": i.product.name, "quantity": i.quantity, "allocated": i.allocated, "available": i.product.available, "location": i.product.location} for i in o.items]
        })
    return result

@app.post("/api/orders")
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    if not payload.items: raise HTTPException(400, "Order must have at least one item")
    order = CustomerOrder(customer=payload.customer, priority=payload.priority, notes=payload.notes, status=OrderStatus.CREATED.value)
    db.add(order); db.flush()
    total = 0
    for item in payload.items:
        product = db.query(Product).filter(Product.sku == item.sku).first()
        if not product: raise HTTPException(404, f"SKU not found: {item.sku}")
        db.add(OrderItem(order_id=order.id, product_id=product.id, quantity=item.quantity))
        total += item.quantity
    order.total_items = total
    db.add(Task(order_id=order.id, task_type="Allocation Review", priority=order.priority))
    db.commit(); db.refresh(order)
    return {"message": "Order created", "order_id": order.id}

@app.post("/api/orders/{order_id}/allocate")
def allocate_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(CustomerOrder, order_id)
    if not order: raise HTTPException(404, "Order not found")
    if order.status in [OrderStatus.DISPATCHED.value, OrderStatus.CANCELLED.value]:
        raise HTTPException(400, "Order cannot be allocated in its current status")
    allocated_total = 0
    partial_notes = []
    for item in order.items:
        product = item.product
        need = item.quantity - item.allocated
        can_allocate = min(need, product.available)
        if can_allocate > 0:
            product.reserved += can_allocate
            item.allocated += can_allocate
            allocated_total += can_allocate
        if can_allocate < need:
            partial_notes.append(f"{product.sku}: need {need}, allocated {can_allocate}")
            db.add(ExceptionLog(order_id=order.id, product_id=product.id, exception_type="Stock Shortage", message=f"{product.name} short by {need-can_allocate}", decision="Prioritize this order and allocate available stock", resolution="Open"))
    order.allocated_items = allocated_total
    if allocated_total == order.total_items:
        order.status = OrderStatus.ALLOCATED.value
        db.add(Task(order_id=order.id, task_type="Picking", priority=order.priority))
        decision = "Fully allocated; create picking task"
    elif allocated_total > 0:
        order.status = OrderStatus.PARTIAL.value
        decision = "Partially allocated; exception logged for short stock"
    else:
        order.status = OrderStatus.CREATED.value
        decision = "No stock allocated; wait / recommend replenishment"
    order.notes = (order.notes + " | " + "; ".join(partial_notes)).strip(" |")
    db.commit()
    return {"order_id": order_id, "status": order.status, "allocated_items": allocated_total, "decision": decision, "shortages": partial_notes}

@app.get("/api/tasks")
def get_tasks(db: Session = Depends(get_db)):
    return [{"id": t.id, "order_id": t.order_id, "task_type": t.task_type, "status": t.status, "assigned_to": t.assigned_to, "priority": t.priority, "created_at": t.created_at.isoformat()} for t in db.query(Task).order_by(Task.priority.desc(), Task.created_at.asc()).all()]

@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, status: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task: raise HTTPException(404, "Task not found")
    task.status = status
    if status == "Completed":
        order = db.get(CustomerOrder, task.order_id)
        if task.task_type == "Picking":
            order.status = OrderStatus.PICKING.value
            db.add(Task(order_id=order.id, task_type="Packing", priority=order.priority))
        elif task.task_type == "Packing":
            order.status = OrderStatus.PACKED.value
            db.add(Task(order_id=order.id, task_type="Quality Check", priority=order.priority))
        elif task.task_type == "Quality Check":
            order.status = OrderStatus.QUALITY_CHECK.value
            db.add(Task(order_id=order.id, task_type="Dispatch", priority=order.priority))
        elif task.task_type == "Dispatch":
            order.status = OrderStatus.DISPATCHED.value
            for item in order.items:
                item.product.reserved = max(0, item.product.reserved - item.allocated)
                item.product.stock = max(0, item.product.stock - item.allocated)
    db.commit()
    return {"message": "Task updated", "task_id": task_id, "status": task.status}

@app.get("/api/exceptions")
def get_exceptions(db: Session = Depends(get_db)):
    return [{"id": e.id, "order_id": e.order_id, "product_id": e.product_id, "type": e.exception_type, "message": e.message, "decision": e.decision, "resolution": e.resolution, "created_at": e.created_at.isoformat()} for e in db.query(ExceptionLog).order_by(ExceptionLog.created_at.desc()).all()]

@app.post("/api/exceptions")
def create_exception(payload: ExceptionCreate, db: Session = Depends(get_db)):
    e = ExceptionLog(**payload.model_dump())
    db.add(e); db.commit(); db.refresh(e)
    return {"message": "Exception logged", "id": e.id}

@app.patch("/api/exceptions/{exception_id}/resolve")
def resolve_exception(exception_id: int, db: Session = Depends(get_db)):
    e = db.get(ExceptionLog, exception_id)
    if not e: raise HTTPException(404, "Exception not found")
    e.resolution = "Resolved"
    db.commit()
    return {"message": "Exception resolved"}

@app.get("/api/analytics")
def analytics(db: Session = Depends(get_db)):
    products = db.query(Product).all(); orders = db.query(CustomerOrder).all()
    by_status = {}
    for o in orders: by_status[o.status] = by_status.get(o.status, 0) + 1
    category = {}
    for p in products: category[p.category] = category.get(p.category, 0) + p.stock
    return {
        "orders_by_status": by_status,
        "units_by_category": category,
        "top_stock_risks": [product_dict(p) for p in sorted(products, key=lambda x: x.available - x.reorder_level)[:5]],
        "priority_breakdown": {str(n): len([o for o in orders if o.priority == n]) for n in range(1,6)},
    }
