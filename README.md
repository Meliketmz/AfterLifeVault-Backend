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

Mail gönderimi için SMTP bilgilerini de ekleyin:

```env
SMTP_SERVER="smtp.example.com"
SMTP_LOGIN="user@example.com"
SMTP_PASSWORD="your-password"
SMTP_PORT=587
MAIL_FROM="source@example.com"
```

`EmailSender` sınıfı 465 portunda SSL, diğer portlarda STARTTLS kullanır.

## Veritabanını oluşturma

Tabloları ve gerekli indexleri Neon üzerinde oluşturmak için:

```bash
python init_db.py
```

Komut tekrar çalıştırılabilir; mevcut tablolar silinmez.

## Çalıştırma

```bash
uvicorn main:app --reload
```

API: <http://127.0.0.1:8000/api/hello>  
Swagger dokümantasyonu: <http://127.0.0.1:8000/docs>

Vault CRUD endpointleri `/api/vault-items` altında bulunur. Listeleme, görüntüleme,
güncelleme ve silme işlemlerinde `owner_user_id` query parametresi zorunludur.

Access Code CRUD endpointleri `/api/access-codes` altında bulunur. Listeleme,
görüntüleme, güncelleme ve silme işlemlerinde `recipient_id` query parametresi
zorunludur. `code_hash` API yanıtlarında döndürülmez.

Uygulama, bulunamayan kaynaklar için `404`, yetkisiz erişimler için `403` durum kodu ve JSON yanıt döndürür.
