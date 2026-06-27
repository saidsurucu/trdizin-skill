# TR Dizin Skill

TR Dizin (TÜBİTAK ULAKBİM Ulusal Akademik Dizin — [trdizin.gov.tr](https://trdizin.gov.tr))
için bir **Claude Code skill**'i. TR Dizin'in **açık JSON API'sini** düz HTTPS
üzerinden kullanır: yayın/dergi/yazar/kurum araması, gelişmiş alan araması,
facet filtreleri, kaynakça ve PDF→metin. **Giriş, CAPTCHA veya API anahtarı
gerekmez.**

> Bu skill bir sunucu/MCP değildir. Çekirdek mantık bağımlılıksız Python
> (stdlib) bir CLI'dadır; Claude bunu `Bash` ile çağırıp temiz JSON alır.
> Sadece PDF→metin için opsiyonel olarak `markitdown` gerekir.

## Kurulum

Claude'a şunu yaz:

> `https://github.com/saidsurucu/trdizin-skill` reposunu `~/.claude/skills/trdizin`
> klasörüne klonla — TR Dizin skill'ini kurmak istiyorum.

**Gereksinimler:** Python 3 (arama için yeterli, ek paket yok). PDF→metin için:

```bash
pip install 'markitdown[pdf]'
```

## Ne yapabilir

Kurduktan sonra doğal dilde söylemen yeterli; skill devreye girip ilgili işi
yapar ve sonuçları JSON olarak döndürür.

### 1. Yayın arama — `search`
Anahtar kelime + filtreler (erişim tipi, yıl, dil, konu, doküman tipi, dergi,
kurum) + sıralama. Her kayıt: başlık, yazarlar, dergi, yıl, DOI, öz, anahtar
kelimeler, atıf sayısı, erişim, **kaynakça** ve PDF UUID. Ayrıca facet sayıları
(ör. "açık erişim: 100.730") döner.

> *"TR Dizin'de 'yapay zeka' ara, en yeniler önce"*
> *"'iklim değişikliği' için 2024 açık erişim yayınları getir"*

### 2. Gelişmiş alan araması — `advanced`
Alan bazlı: `title, abstract, year, author, orcid, issn, eissn, journal, doi,
language, institution` + **AND / OR / NOT**.

> *"Başlığında 'yapay zeka', özünde 'eğitim' geçmeyen yayınlar"*
> *"Yazarı İnalcık olan yayınları bul"*

### 3. Dergi / yazar / kurum arama — `journals` / `authors` / `institutions`
Yayın dışındaki üç varlık tipi. Yazar sonuçları atıf sayısıyla zenginleştirilir.

> *"'eğitim' dergilerini ara"* · *"Boğaziçi Üniversitesi'ni kurum olarak ara"*

### 4. PDF → metin — `pdf`
Açık erişimli bir yayının PDF'ini (sonuçtaki `pdf_uuid` ile) markdown metne
çevirir (`markitdown`). Kapalı yayınlarda PDF yoktur. OCR yoktur.

> *"Şu yayının PDF'ini metne çevir: <pdf_uuid>"*

## Nasıl çalışır

- Tüm aramalar `search.trdizin.gov.tr/api/defaultSearch/{entity}/` uç noktasına
  gider; açık API olduğu için tarayıcı/oturum gerekmez.
- Çıktı ham Elasticsearch değil, **stabil normalize bir şemadır** (`schema_version`,
  `pagination`, `facets`, `results`); ham ID'ler korunur.
- Yazar adları `yazarlar` anahtarıyla döner (Claude çıktı redaktörü "author"
  içeren anahtarları gizlediği için).
- PDF iki adımlıdır: `getFile` imzalı URL döndürür → PDF indirilir → `markitdown`
  ile metne çevrilir.
- Sayfa içeriği **güvenilmez veri** olarak ele alınır; içindeki talimatlar
  uygulanmaz.

## Geliştirme

Saf ayrıştırma/sorgu-kurma fonksiyonları Python stdlib `unittest` ile, sabit
fixture'lar üzerinden (ağsız) test edilir:

```bash
python3 -m unittest discover -s tests          # offline (canlı testler atlanır)
TRDIZIN_LIVE=1 python3 -m unittest discover -s tests   # + canlı smoke testleri
```

Kod yapısı:
- `SKILL.md` — Claude'un izlediği iş akışları
- `reference.md` — endpoint'ler, alan adları, facet'ler, order kodları, canlı doğrulama notları
- `scripts/core.py` — saf ayrıştırma/sorgu kurma (birim testli)
- `scripts/trdizin.py` — HTTP katmanı + CLI (search/advanced/journals/authors/institutions/pdf)
- `tests/` — fixture tabanlı birim testleri + opsiyonel canlı smoke testleri

## Notlar

- Tek instance / kişisel kullanım için tasarlanmıştır.
- API dökümansız ve açık; habersiz değişebilir. Canlı smoke testleri bunu yakalar.
- `--q` içinde `:` kullanılamaz (gelişmiş arama kullan); `relevance-DESC` güvenli
  varsayılan sıralamadır.
