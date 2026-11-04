# AfterLifeVault Backend

FastAPI ve uzak PostgreSQL bağlantı havuzu içeren küçük bir backend uygulaması.

## Kurulum

```bash
git clone https://github.com/Meliketmz/AfterLifeVault-backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`.env` dosyasını oluşturup PostgreSQL bağlantı bilgilerini ekleyin:

```env
DATABASE_URL_POOLED="postgresql://..."
DATABASE_URL="postgresql://..."
```

`DATABASE_URL_POOLED` varsa öncelikli olarak kullanılır.

## Çalıştırma

```bash
uvicorn main:app --reload
```

API: <http://127.0.0.1:8000/api/hello>  
Swagger dokümantasyonu: <http://127.0.0.1:8000/docs>

Uygulama, bulunamayan kaynaklar için `404`, yetkisiz erişimler için `403` durum kodu ve JSON yanıt döndürür.
