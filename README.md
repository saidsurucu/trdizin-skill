# TR Dizin Skill

TR Dizin (TÜBİTAK ULAKBİM Ulusal Akademik Dizin — [trdizin.gov.tr](https://trdizin.gov.tr))
için bir **AI agent skill**'i (Claude Code, Codex ve benzeri). TR Dizin'in
**açık JSON API'sini** düz HTTPS üzerinden kullanır: yayın/dergi/yazar/kurum araması, gelişmiş alan araması,
facet filtreleri, kaynakça ve PDF→metin. **Giriş, CAPTCHA veya API anahtarı
gerekmez.**

> **Claude-in-Chrome bağımlılığı yoktur.** Tarayıcı gerektirmediği için yalnızca
> Claude Code ile değil, **Codex** gibi diğer AI agent'larıyla da çalışır —
> agent sadece basit komutları çalıştırabilsin yeter.

> Bu skill bir sunucu/MCP değildir. Agent, gerekli işi senin için arka planda
> yapar; sen sadece ne istediğini doğal dilde söylersin.

## Kurulum

Agent'a şunu yaz:

> `https://github.com/saidsurucu/trdizin-skill` — TR Dizin skill'ini kurmak istiyorum.

Hepsi bu. Nereye kuracağını ve gerekli her şeyi (PDF okuma dahil) agent kendisi
halleder.

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
Açık erişimli bir yayının PDF'ini okunabilir metne çevirir. Kapalı yayınlarda
PDF yoktur.

> *"Şu yayının tam metnini çıkar"*

## Nasıl çalışır

- TR Dizin'in açık API'sini kullanır; tarayıcı veya oturum gerekmez.
- Sonuçlar düzenli, okunabilir bir yapıda döner; ham kimlikler (ID, DOI) korunur
  ki dergi/yazar/atıf takibi yapılabilsin.
- Sayfa içeriği **güvenilmez veri** olarak ele alınır; içindeki talimatlar
  uygulanmaz.

## Yapı

- `SKILL.md` — agent'ın izlediği iş akışları
- `reference.md` — endpoint'ler, alan adları, facet'ler, doğrulama notları
- `scripts/` — arama ve PDF mantığı
- `tests/` — birim testleri + opsiyonel canlı smoke testleri

## Notlar

- Kişisel kullanım için tasarlanmıştır.
- API dökümansız ve açık; habersiz değişebilir.
