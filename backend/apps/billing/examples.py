"""
Billing sistemi kullanım örnekleri.

Bu dosya billing sisteminin nasıl kullanılacağına dair örnek kodlar içerir.
Bu örnekler Django shell'de veya view'larda kullanılabilir.

Kullanım:
    python manage.py shell
    >>> from billing.examples import *
    >>> example_1_subscription_purchase()
"""

from django.db import transaction
from django.contrib.auth import get_user_model
from decimal import Decimal

from billing.models import (
    SubscriptionPlan, SMSPackage, TenantSubscription,
    Payment, SmsBalance, SmsTransaction
)
from billing.services import (
    SubscriptionService, SmsService, PaymentService
)
from tenants.models import Company

User = get_user_model()


# =============================================================================
# ÖRNEK 1: Tenant Subscription Plan Satın Alıyor
# =============================================================================

@transaction.atomic
def example_1_subscription_purchase():
    """
    Senaryo: Yeni bir tenant premium plan satın alıyor ve iyzico ile ödeme yapıyor.
    """
    print("\n" + "="*70)
    print("ÖRNEK 1: Tenant Subscription Plan Satın Alıyor")
    print("="*70 + "\n")

    # 1. Test verilerini hazırla
    tenant, created = Company.objects.get_or_create(
        name='Örnek Şirket A.Ş.',
        defaults={
            'slug': 'ornek-sirket',
            'email': 'info@ornek-sirket.com',
            'phone': '+905551234567',
            'address': 'İstanbul'
        }
    )
    print(f"✓ Tenant: {tenant.name}")

    # 2. Premium planı seç
    plan, created = SubscriptionPlan.objects.get_or_create(
        slug='premium',
        defaults={
            'name': 'Premium Plan',
            'description': 'Tam özellikli premium plan',
            'price': Decimal('299.00'),
            'billing_cycle': 'monthly',
            'max_employees': 50,
            'max_products': 1000,
            'has_inventory': True,
            'welcome_sms_bonus': 100,  # 100 SMS hediye
        }
    )
    print(f"✓ Plan: {plan.name} - {plan.price} TL/ay")
    print(f"  - Maksimum çalışan: {plan.max_employees}")
    print(f"  - Hoşgeldin bonusu: {plan.welcome_sms_bonus} SMS")

    # 3. Subscription oluştur
    subscription = SubscriptionService.create_subscription(
        tenant=tenant,
        plan=plan,
        duration_months=1,
        notes='İlk abonelik - Premium'
    )
    print(f"\n✓ Subscription oluşturuldu: {subscription}")
    print(f"  - Durum: {subscription.status}")
    print(f"  - Başlangıç: {subscription.started_at}")
    print(f"  - Bitiş: {subscription.expires_at}")

    # 4. Payment oluştur
    payment = PaymentService.create_subscription_payment(
        tenant=tenant,
        subscription=subscription,
        payment_method='iyzico'
    )
    print(f"\n✓ Payment oluşturuldu: #{payment.id}")
    print(f"  - Tutar: {payment.amount} {payment.currency}")
    print(f"  - Durum: {payment.status}")

    # 5. Ödeme tamamlandı (iyzico callback simülasyonu)
    PaymentService.complete_payment(
        payment=payment,
        gateway_transaction_id='iyzico_tx_123456789',
        gateway_data={
            'conversationId': 'conv_123',
            'paymentStatus': 'SUCCESS'
        }
    )
    print(f"\n✓ Ödeme tamamlandı!")
    print(f"  - Transaction ID: {payment.gateway_transaction_id}")

    # 6. Sonuçları kontrol et
    subscription.refresh_from_db()
    print(f"\n✓ Subscription durumu: {subscription.status}")

    # Welcome bonus kontrolü
    sms_balance = SmsService.check_balance(tenant)
    print(f"✓ SMS Bakiyesi: {sms_balance} SMS")
    print(f"  (Plan hoşgeldin bonusu otomatik eklendi)")

    # İşlem geçmişi
    transactions = SmsTransaction.objects.filter(tenant=tenant)
    print(f"\n✓ SMS İşlem Geçmişi:")
    for tx in transactions:
        print(f"  - {tx.get_transaction_type_display()}: {tx.amount} SMS")

    print("\n" + "="*70 + "\n")

    return {
        'tenant': tenant,
        'subscription': subscription,
        'payment': payment,
        'sms_balance': sms_balance
    }


# =============================================================================
# ÖRNEK 2: Tenant SMS Paketi Satın Alıyor (Banka Havalesi)
# =============================================================================

@transaction.atomic
def example_2_sms_package_purchase():
    """
    Senaryo: Tenant SMS paketi satın alıyor ve banka havalesi ile ödüyor.
    Admin onayladıktan sonra SMS kredileri yükleniyor.
    """
    print("\n" + "="*70)
    print("ÖRNEK 2: Tenant SMS Paketi Satın Alıyor (Banka Havalesi)")
    print("="*70 + "\n")

    # 1. Tenant getir
    tenant = Company.objects.first()
    if not tenant:
        tenant = Company.objects.create(
            name='Test Şirketi',
            slug='test-sirket',
            email='test@test.com'
        )
    print(f"✓ Tenant: {tenant.name}")

    # Başlangıç bakiyesi
    initial_balance = SmsService.check_balance(tenant)
    print(f"✓ Mevcut SMS bakiyesi: {initial_balance}")

    # 2. SMS paketi seç
    package, created = SMSPackage.objects.get_or_create(
        name='sms_1000',
        defaults={
            'display_name': '1000 SMS Paketi',
            'description': 'Toplu SMS gönderimleriniz için ideal paket',
            'sms_credits': 1000,
            'bonus_credits': 100,  # 100 bonus SMS
            'price': Decimal('450.00'),
            'is_active': True,
            'sort_order': 2
        }
    )
    print(f"\n✓ Paket: {package.display_name}")
    print(f"  - Temel kredi: {package.sms_credits} SMS")
    print(f"  - Bonus kredi: {package.bonus_credits} SMS")
    print(f"  - Toplam: {package.get_total_credits()} SMS")
    print(f"  - Fiyat: {package.price} TL")
    print(f"  - SMS başına: {package.get_price_per_sms():.4f} TL")

    # 3. Payment oluştur (Banka Havalesi)
    payment = PaymentService.create_sms_payment(
        tenant=tenant,
        package=package,
        payment_method='bank_transfer'
    )
    print(f"\n✓ Payment oluşturuldu: #{payment.id}")
    print(f"  - Tutar: {payment.amount} {payment.currency}")
    print(f"  - Metod: {payment.get_payment_method_display()}")
    print(f"  - Durum: {payment.status}")

    # 4. Kullanıcı banka havalesi yaptı (simülasyon)
    payment.bank_reference = 'REF2026012912345'
    payment.notes = 'Ziraat Bankası üzerinden havale yapıldı'
    payment.save()
    print(f"\n✓ Banka referansı kaydedildi: {payment.bank_reference}")

    # 5. Admin onayı
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()

    print(f"\n✓ Admin onayı bekleniyor...")
    payment.approve(admin_user)
    print(f"✓ Ödeme admin tarafından onaylandı!")
    print(f"  - Onaylayan: {payment.approved_by.username}")
    print(f"  - Onay zamanı: {payment.approved_at}")

    # 6. Sonuçları kontrol et
    payment.refresh_from_db()
    final_balance = SmsService.check_balance(tenant)

    print(f"\n✓ Payment durumu: {payment.status}")
    print(f"✓ SMS Bakiyesi:")
    print(f"  - Önceki: {initial_balance} SMS")
    print(f"  - Sonraki: {final_balance} SMS")
    print(f"  - Eklenen: {final_balance - initial_balance} SMS")

    # Son işlemler
    recent_tx = SmsTransaction.objects.filter(
        tenant=tenant,
        transaction_type='purchase'
    ).order_by('-created_at').first()

    if recent_tx:
        print(f"\n✓ İşlem Kaydı:")
        print(f"  - Tip: {recent_tx.get_transaction_type_display()}")
        print(f"  - Miktar: +{recent_tx.amount} SMS")
        print(f"  - Sonraki bakiye: {recent_tx.balance_after} SMS")
        print(f"  - Açıklama: {recent_tx.description}")

    print("\n" + "="*70 + "\n")

    return {
        'tenant': tenant,
        'package': package,
        'payment': payment,
        'initial_balance': initial_balance,
        'final_balance': final_balance
    }


# =============================================================================
# ÖRNEK 3: SMS Gönderimi ve Kredi Kullanımı
# =============================================================================

@transaction.atomic
def example_3_sms_usage():
    """
    Senaryo: Tenant SMS gönderiyor ve her gönderimdekredisi düşüyor.
    """
    print("\n" + "="*70)
    print("ÖRNEK 3: SMS Gönderimi ve Kredi Kullanımı")
    print("="*70 + "\n")

    # 1. Tenant getir
    tenant = Company.objects.first()
    if not tenant:
        print("❌ Önce Örnek 1 veya 2'yi çalıştırın")
        return

    print(f"✓ Tenant: {tenant.name}")

    # 2. Başlangıç bakiyesi
    initial_balance = SmsService.check_balance(tenant)
    print(f"✓ Başlangıç bakiyesi: {initial_balance} SMS")

    # Bakiye yoksa ekle
    if initial_balance < 10:
        print("\n⚠ Yetersiz bakiye, 100 SMS bonus ekleniyor...")
        SmsService.add_credits(
            tenant=tenant,
            amount=100,
            description='Test için bonus kredi'
        )
        initial_balance = SmsService.check_balance(tenant)
        print(f"✓ Yeni bakiye: {initial_balance} SMS")

    # 3. SMS gönderim simülasyonu
    print("\n✓ SMS Gönderimi Başlıyor...")
    sms_campaigns = [
        {'name': 'Kampanya Duyurusu', 'recipients': 5},
        {'name': 'Hoşgeldiniz Mesajı', 'recipients': 3},
        {'name': 'Randevu Hatırlatma', 'recipients': 2},
    ]

    for campaign in sms_campaigns:
        name = campaign['name']
        count = campaign['recipients']

        # Bakiye kontrolü
        if not SmsService.has_sufficient_credits(tenant, count):
            print(f"  ❌ {name}: Yetersiz kredi! (Gerekli: {count})")
            break

        # SMS gönder (simülasyon)
        print(f"  📤 {name}: {count} alıcıya gönderiliyor...")

        # Kredi düş
        SmsService.deduct_credits(
            tenant=tenant,
            amount=count,
            description=f'{name} - {count} alıcı'
        )

        current_balance = SmsService.check_balance(tenant)
        print(f"     ✓ Gönderildi! Kalan bakiye: {current_balance} SMS")

    # 4. Özet
    final_balance = SmsService.check_balance(tenant)
    total_used = initial_balance - final_balance

    print(f"\n✓ Özet:")
    print(f"  - Başlangıç: {initial_balance} SMS")
    print(f"  - Kullanılan: {total_used} SMS")
    print(f"  - Kalan: {final_balance} SMS")

    # 5. Son işlemler
    print(f"\n✓ Son 5 İşlem:")
    recent_transactions = SmsTransaction.objects.filter(
        tenant=tenant
    ).order_by('-created_at')[:5]

    for tx in recent_transactions:
        sign = '+' if tx.amount > 0 else ''
        print(f"  - {tx.created_at.strftime('%Y-%m-%d %H:%M')}: "
              f"{tx.get_transaction_type_display()} {sign}{tx.amount} SMS "
              f"(Bakiye: {tx.balance_after})")

    print("\n" + "="*70 + "\n")

    return {
        'tenant': tenant,
        'initial_balance': initial_balance,
        'final_balance': final_balance,
        'total_used': total_used
    }


# =============================================================================
# ÖRNEK 4: Admin SMS Kredisi Ekleme (Bonus/Düzeltme)
# =============================================================================

@transaction.atomic
def example_4_admin_add_credits():
    """
    Senaryo: Admin tenant'a bonus SMS kredisi ekliyor.
    """
    print("\n" + "="*70)
    print("ÖRNEK 4: Admin SMS Kredisi Ekleme (Bonus)")
    print("="*70 + "\n")

    # 1. Tenant ve Admin
    tenant = Company.objects.first()
    if not tenant:
        print("❌ Önce Örnek 1 veya 2'yi çalıştırın")
        return

    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'is_staff': True,
            'is_superuser': True
        }
    )

    print(f"✓ Tenant: {tenant.name}")
    print(f"✓ Admin: {admin_user.username}")

    # 2. Mevcut bakiye
    before_balance = SmsService.check_balance(tenant)
    print(f"\n✓ Mevcut bakiye: {before_balance} SMS")

    # 3. Bonus ekle
    bonus_amount = 250
    print(f"\n✓ {bonus_amount} SMS bonus ekleniyor...")

    SmsService.add_credits(
        tenant=tenant,
        amount=bonus_amount,
        user=admin_user,
        description='Yeni yıl promosyonu - Ücretsiz 250 SMS'
    )

    # 4. Sonuç
    after_balance = SmsService.check_balance(tenant)
    print(f"✓ İşlem tamamlandı!")
    print(f"  - Önceki bakiye: {before_balance} SMS")
    print(f"  - Eklenen: +{bonus_amount} SMS")
    print(f"  - Yeni bakiye: {after_balance} SMS")

    # İşlem kaydı
    bonus_tx = SmsTransaction.objects.filter(
        tenant=tenant,
        transaction_type='bonus'
    ).order_by('-created_at').first()

    if bonus_tx:
        print(f"\n✓ İşlem Kaydı:")
        print(f"  - Tip: {bonus_tx.get_transaction_type_display()}")
        print(f"  - Miktar: +{bonus_tx.amount} SMS")
        print(f"  - Açıklama: {bonus_tx.description}")
        print(f"  - Ekleyen: {bonus_tx.created_by.username if bonus_tx.created_by else 'Sistem'}")

    print("\n" + "="*70 + "\n")

    return {
        'tenant': tenant,
        'before_balance': before_balance,
        'after_balance': after_balance,
        'bonus_amount': bonus_amount
    }


# =============================================================================
# ÖRNEK 5: Abonelik ve Limit Kontrolü
# =============================================================================

def example_5_subscription_check():
    """
    Senaryo: Tenant'ın abonelik durumunu ve limitlerini kontrol etme.
    """
    print("\n" + "="*70)
    print("ÖRNEK 5: Abonelik ve Limit Kontrolü")
    print("="*70 + "\n")

    # Tenant getir
    tenant = Company.objects.first()
    if not tenant:
        print("❌ Önce Örnek 1'i çalıştırın")
        return

    print(f"✓ Tenant: {tenant.name}\n")

    # Abonelik durumu
    subscription_info = SubscriptionService.check_subscription_status(tenant)

    if subscription_info['has_subscription']:
        plan = subscription_info['plan']
        print("✓ Aktif Abonelik:")
        print(f"  - Plan: {plan.name}")
        print(f"  - Durum: {subscription_info['status']}")
        print(f"  - Fiyat: {plan.price} TL/{plan.get_billing_cycle_display()}")
        print(f"  - Bitiş Tarihi: {subscription_info['expires_at'].strftime('%Y-%m-%d %H:%M')}")

        print(f"\n✓ Limitler:")
        print(f"  - Maksimum Çalışan: {subscription_info['max_employees']}")

        max_products = subscription_info['max_products']
        print(f"  - Maksimum Ürün: {'Sınırsız' if max_products is None else max_products}")

        print(f"\n✓ Modül Erişimleri:")
        print(f"  - Stok Yönetimi: {'✓' if plan.has_inventory else '✗'}")

        # SMS durumu
        sms_balance = SmsService.check_balance(tenant)
        print(f"\n✓ SMS Durumu:")
        print(f"  - Mevcut Bakiye: {sms_balance} SMS")

        # Örnek limit kontrolü
        current_employee_count = 25  # Örnek
        can_add_employee = plan.check_limit('employees', current_employee_count)
        print(f"\n✓ Limit Kontrolü:")
        print(f"  - Mevcut Çalışan: {current_employee_count}")
        print(f"  - Yeni çalışan eklenebilir mi: {'✓ Evet' if can_add_employee else '✗ Hayır (Limit doldu)'}")

    else:
        print("❌ Aktif abonelik bulunamadı")
        print("  Lütfen önce bir abonelik plan satın alın.")

    print("\n" + "="*70 + "\n")

    return subscription_info


# =============================================================================
# Tüm Örnekleri Çalıştır
# =============================================================================

def run_all_examples():
    """Tüm örnekleri sırayla çalıştır."""
    print("\n" + "="*70)
    print("TÜM ÖRNEKLERİ ÇALIŞTIR")
    print("="*70)

    try:
        # Örnek 1: Subscription satın alma
        result1 = example_1_subscription_purchase()

        # Örnek 2: SMS paketi satın alma
        result2 = example_2_sms_package_purchase()

        # Örnek 3: SMS kullanımı
        result3 = example_3_sms_usage()

        # Örnek 4: Admin bonus ekleme
        result4 = example_4_admin_add_credits()

        # Örnek 5: Durum kontrolü
        result5 = example_5_subscription_check()

        print("\n" + "="*70)
        print("✓ TÜM ÖRNEKLER BAŞARIYLA TAMAMLANDI!")
        print("="*70 + "\n")

        return {
            'example_1': result1,
            'example_2': result2,
            'example_3': result3,
            'example_4': result4,
            'example_5': result5,
        }

    except Exception as e:
        print(f"\n❌ HATA: {str(e)}")
        import traceback
        traceback.print_exc()


# =============================================================================
# Yardımcı Fonksiyonlar
# =============================================================================

def reset_example_data():
    """Test verilerini temizle (dikkatli kullanın!)"""
    print("\n⚠ UYARI: Test verileri siliniyor...\n")

    # Sadece test şirketlerini sil
    test_companies = Company.objects.filter(
        name__in=['Örnek Şirket A.Ş.', 'Test Şirketi']
    )

    for company in test_companies:
        print(f"  - Siliniyor: {company.name}")
        company.delete()

    print("\n✓ Test verileri temizlendi.\n")


def show_help():
    """Kullanım talimatlarını göster"""
    help_text = """
    ╔══════════════════════════════════════════════════════════════════╗
    ║                BILLING EXAMPLES - KULLANIM KLAVUZU               ║
    ╚══════════════════════════════════════════════════════════════════╝

    Django shell'de çalıştırın:
        python manage.py shell

    Ardından:
        >>> from billing.examples import *

    Örnekleri tek tek çalıştırın:
        >>> example_1_subscription_purchase()   # Abonelik satın alma
        >>> example_2_sms_package_purchase()    # SMS paketi satın alma
        >>> example_3_sms_usage()               # SMS kullanımı
        >>> example_4_admin_add_credits()       # Admin bonus ekleme
        >>> example_5_subscription_check()      # Durum kontrolü

    Veya tümünü çalıştırın:
        >>> run_all_examples()

    Test verilerini temizleyin:
        >>> reset_example_data()

    Yardım:
        >>> show_help()

    ═══════════════════════════════════════════════════════════════════
    """
    print(help_text)


# Modül yüklendiğinde yardımı göster
if __name__ != '__main__':
    print("\n✓ Billing examples yüklendi!")
    print("  Kullanım için: show_help()")
