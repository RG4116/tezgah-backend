from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from database import SessionLocal, engine
from models import Base, Product, Color
from pydantic import BaseModel
import pandas as pd
from io import BytesIO

app = FastAPI()

# ✅ CORS Ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ✅ Veritabanını oluştur
Base.metadata.create_all(bind=engine)

# ✅ Veritabanı bağlantısı
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Pydantic Modelleri
class ProductCreate(BaseModel):
    name: str

class ColorCreate(BaseModel):
    product_id: int
    name: str
    price: float
    currency: str

# ✅ Renk Güncelleme için Yeni Model
class ColorUpdate(BaseModel):
    name: str
    price: float
    currency: str  # Para birimi için opsiyonel enum eklenebilir

# ✅ Ürünleri Getir
@app.get("/products/")
def get_products(db: Session = Depends(get_db)):
    products = db.query(Product).options(joinedload(Product.colors)).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "colors": [
                {
                    "id": c.id,
                    "name": c.name,
                    "price": c.price,
                    "currency": c.currency
                } for c in p.colors
            ]
        }
        for p in products
    ]

# ✅ Ürün Ekle
@app.post("/products/")
def add_product(product: ProductCreate, db: Session = Depends(get_db)):
    new_product = Product(name=product.name)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return {"message": "Ürün eklendi!", "id": new_product.id}

# ✅ Renkleri Getir
@app.get("/colors/")
def get_colors(db: Session = Depends(get_db)):
    colors = db.query(Color).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "price": c.price,
            "currency": c.currency,
            "product_id": c.product_id
        } for c in colors
    ]

# ✅ Renk Ekle
@app.post("/colors/")
def add_color(color: ColorCreate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == color.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    new_color = Color(
        name=color.name,
        product_id=color.product_id,
        price=color.price,
        currency=color.currency
    )
    db.add(new_color)
    db.commit()
    db.refresh(new_color)

    return {"message": "Renk eklendi!", "id": new_color.id}

# ✅ Ürün Güncelleme
@app.put("/products/{product_id}")
def update_product(product_id: int, product: ProductCreate, db: Session = Depends(get_db)):
    existing_product = db.query(Product).filter(Product.id == product_id).first()
    if not existing_product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    existing_product.name = product.name
    db.commit()
    return {"message": "Ürün güncellendi!"}

# ✅ Renk Güncelleme (GÜNCELLENDİ)
@app.put("/colors/{color_id}")
def update_color(color_id: int, color: ColorUpdate, db: Session = Depends(get_db)):  # ColorUpdate kullanılıyor
    existing_color = db.query(Color).filter(Color.id == color_id).first()
    if not existing_color:
        raise HTTPException(status_code=404, detail="Renk bulunamadı")

    existing_color.name = color.name
    existing_color.price = color.price
    existing_color.currency = color.currency

    db.commit()
    return {"message": "Renk güncellendi!"}

# ✅ Ürün Sil
@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    db.delete(product)
    db.commit()
    return {"message": "Ürün silindi!"}

# ✅ Renk Sil
@app.delete("/colors/{color_id}")
def delete_color(color_id: int, db: Session = Depends(get_db)):
    color = db.query(Color).filter(Color.id == color_id).first()
    if not color:
        raise HTTPException(status_code=404, detail="Renk bulunamadı")

    db.delete(color)
    db.commit()
    return {"message": "Renk silindi!"}

# ✅ Excel Yükleme
@app.post("/upload-excel/")
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Lütfen .xlsx formatında bir dosya yükleyin")

    contents = await file.read()

    try:
        excel_data = pd.read_excel(BytesIO(contents))
        excel_data.columns = excel_data.columns.str.strip()  # ✅ Sütun başlıklarındaki boşlukları sil
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Excel dosyası okunamadı: {str(e)}")

    required_columns = {"Ürün Adı", "Renk", "Fiyat", "Para Birimi"}
    if not required_columns.issubset(excel_data.columns):
        raise HTTPException(status_code=400, detail="Excel dosyasında eksik sütun var!")

    # ✅ Satır boşluklarını ve eksik verileri temizle
    excel_data = excel_data.dropna(subset=["Ürün Adı", "Renk", "Fiyat", "Para Birimi"])
    excel_data["Ürün Adı"] = excel_data["Ürün Adı"].astype(str).str.strip()
    excel_data["Renk"] = excel_data["Renk"].astype(str).str.strip()
    excel_data["Para Birimi"] = excel_data["Para Birimi"].astype(str).str.strip()

    for _, row in excel_data.iterrows():
        product = db.query(Product).filter(Product.name == row["Ürün Adı"]).first()
        if not product:
            product = Product(name=row["Ürün Adı"])
            db.add(product)
            db.commit()
            db.refresh(product)

        # ✅ Aynı ürün ve aynı renk zaten varsa ekleme
        color_exists = db.query(Color).filter(
            Color.name == row["Renk"],
            Color.product_id == product.id
        ).first()

        if color_exists:
            continue

        new_color = Color(
            name=row["Renk"],
            price=row["Fiyat"],
            currency=row["Para Birimi"],
            product_id=product.id
        )
        db.add(new_color)

    db.commit()
    return {"message": "Excel başarıyla yüklendi!"}

