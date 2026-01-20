MULTI TENANT SETTINGS:
1.business setup
1.1.business detail
fields:
-name
-currency (currencies, default:country.currency)
-tax calculation(options: default:retail prices exlude tax, retail prices include tax)
-team default language(languages,default:tr)
-client default language(languages,default:tr)
-facebook
-instagram
-x
-website
-country (countries based on geolocation, do not let client change it)

    notes:
    	Team members and clients can override the language displayed to them in their settings.

1.2 locations
contact details:
fields:
-name
-number ( default prefix country.phone_code)
-email
business type:
fields:
main = foreing key businessType
additional = many2many businessType max 2
other = charfield
location details:
fields:
-address
-apt/suite etc
-district
-city (charfield)
-postcode
-country (business.country)
-latitude
-longitude
billing details:
fields:
-company name
-address
-city
-state
-postcode
-invoice note
description: billing detail is based on location, should have bool:use location info as default address/city etc.
####can be deleted####
tipping details:
fields:
-tip value ( 100>value>0)
-bool: services (default:true)
-bool: service-addons (default:true)
-bool: products (default:true)
-bool: membership (default:true)
-bool: gift cards (default:true)
-service charges (included(default)|excluded)
-discounts (included(default)|excluded)
-taxes (included(default)|excluded)
description: there should be a boolean use company defaults. tip value can be stored as charfield array like 10|15|25 or json field. max 5 items atleast 1. defaults: 10-15-25. company default 3.4.2 tipping details. tip ( 100>value>0)
###################################
working hours:
fields:
-working_hours: json field. default dict sunday closed, other day 10:00-19:00

1.3 client sources
fields:
-name
-is_active
-order
-is_system default:False
description:
copy Platform clientResource with is_active flag add to here. is_system obj can not be deleted/edited by tenant. only edit order if has field

2.scheduling setup
2.1 time and calendar
time details:
fields:
-timezone (default istanbul)
-timeformat (options: 12|24(default))
-firstday of week : monday default
calendar details:
fields:
-Appointment color source (options: Category(default)|Team Member|Status)
-Display processing time segments within appointment tiles (bool , default:True, description:Extra processing time that is part of an appointment will be shown as a faded segment in the same color as the appointment tile. Learn more)
-Highlight blocked time segments within appointment tiles(bool , default:True, description:Extra blocked time that is part of an appointment will be shown as a grey segment within the appointment tile. Learn more)
2.2 waitlist
fields:
-type: (options: You pick|Automaticaly book)
-waitlist_priority: (options: First in line|highest value| offer to all)
-allow clients join waitlist (bool,default: True)
-client options: Clients can request any preferred time(default)|Clients can only request times that your business is open
description: When waitlist type is set to manual, waitlist automated messages will be disabled. Clients will not be notified when a time slot becomes available. WaitlistPriorty is for Automaticaly book only
2.3 blocked time and types
fields:
-emoji: frontend emoji-picker-react kullanacak
-name
-duration (list, 5 minutes apart,5mins to 8hours 55 mins)
-compensition(paid|unpaid(default))
-is_system: default False
description:
copy Platform blockedTime with is_active flag add to here. is_system obj can not be deleted/edited by tenant. only edit order if has field.
emoji fontfamily: font-family: EmojiMart, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Segoe UI&quot;, &quot;Apple Color Emoji&quot;, &quot;Twemoji Mozilla&quot;, &quot;Noto Color Emoji&quot;, &quot;Android Emoji&quo. will be handle frontend. allow backend support emoji. example:❤️‍
2.4 resources
fields:
-name
-description
-location
2.5 cancelation reasons
fields:
-name
-order
description: copy Platform cancelationReason add to here. is_system obj can not be deleted/edited by tenant. only edit order if has field
2.6 appointment statuses
fields:
-icon: platform.icon
-name
-order
-color: core.constants.COLOR_CHOICES
-is_system
description: copy Platform appointmentStatus add to here. is_system obj can not be deleted/edited by tenant. only edit order if has field

2.7 closed periods
fields:
-start date
-end date
-description
-locations (location model)
descripton:Online bookings cannot be placed when your business is closed.
2.8 onlinebookings
Online availability:
fields:
-clients can book: options: immediatly(default)|15|30mins|1hour|2hour....12hour|1day|2day...6day|1week|2week
-no more than : options 1month|2month|....12months(default)
-client can cancel or reschedule: anytime(default)|30mins|1hour|2|3|4|5|6|12|24|48|72

    	description:
    		New appointment lead time Set how close to the appointment time clients can book, and how far in advance bookings are allowed
    		Cancellation and rescheduling Set how far in advance clients can cancel or reschedule online. After this timeframe clients must call to change their appointment
    Schedule optimization:
    	fields:
    		-Time slot interval: options (5mins,10mins,15mins(default),20mins ....2hours)
    		-inteligent time slots: options(regular time slots(default)|reduce calendar gaps|eleminate calendar gaps)

    	desciption:
    		regular time slots has no other options.
    		reduce calendar gaps depends Allow gaps that are at least (options: 15|20|25|30|35|40|45|50|55|1hour(default)).
    		eleminate calendar gaps: has options (Allow bookings at the start and end of the day(default)|Allow bookings at the start of the day|Allow bookings at the end of the day)
    Online booking options:
    	fields:
    		Allow clients to select team members (bool. default True)
    		Display star ratings and profiles for team members (bool. default True)
    		Display star ratings next to team members (bool. default True)
    		Allow clients to book group appointments (bool. default True) (bool. default True)
    		Display featured services to your clients (bool. default True)
    		Display contact number when clients cannot change appointments (bool. default True)
    Important info:
    	fields:
    		important_info : text_field (description:Display additional information for clients to see when booking an appointment or buying a gift card or membership)

3.sales setup
3.1 payment methods
fields:
-name
-order
-is_system
description: copy Platform paymentMethod add to here. is_system obj can not be deleted/edited by tenant. only edit order if has field
3.2 tax rates
fields:
-name
-rate
3.3 receipts
fields:
-Show client mobile and email (bool. default=True)
-Show client address (bool. default=True)
-Show team members on sale receipt (bool. default=False)
-title: default:sale max 20
-custom line 1 max 100
-custom line 2 max 100
-footer max 225
-Automatically print receipts upon sale completion (bool. default=False)
3.4 tipping
3.4.1 tip
fields:
-value: ( 100>value>0)
description:
copy Platform tip add to here.
3.4.2 tipping details (business default tipping detail)
fields:
-Display a tip option screen at the Point of Sale (bool. default=True)
-bool: services (default:true)
-bool: service-addons (default:true)
-bool: products (default:true)
-bool: membership (default:true)
-bool: gift cards (default:true)
-service charges (included(default)|excluded)
-discounts (included(default)|excluded)
-taxes (included(default)|excluded)
3.5 service charges
fields:
-name
-description (description:For internal use only.)
-Apply service charge on (options: Full sale value (default)|Only selected item types)
-Automatically apply service charge during checkout (bool, default =True)
-rate type: options(flat rate| percentage| both)
-tax rate: options no tax + 3.2 tax rates
condition:
Apply service charge on: Only selected item type: allow mutli select: Services Service add-ons Products Gift cards Memberships
rate type:flat rate: flate rate value (fixed amount moneyusd/try)
rate type:percentage: percentage value, with 2 options Sale total including taxes|Sale subtotal before taxes
rate type:both: support both top
3.6 gift cards
3.6.1 gift card
fields:
-value
3.6.2 gift card options
fields:
-enable (default:false)
-experation: options (1 month|2 month|...|6 months|1eyar|2year|5year|never)

4.billing
4.1 invoices and fees
4.2 subscriptions
4.3 billing details
5.team
5.1 Time off types
fields:
-name
description: copy Platform Time off types add to here. is_system obj can not be deleted/edited by tenant. only edit order if has field
5.2 Permissions
have 5 mods: Basic Low Med High Owner
Locations:
Access all locations: > basic
Bookings & Clients
Access own calendar: all, not editable
Access other staff calendars: all,editable
Can book appointments > basic
Can apply discounts to appointments >low
Home >med
Clients >basic
Can see client contact info >basic
Can download clients > low
Messages >basic
Manage own blocked times >basic
Manage all blocked times >basic
Manage blocked time types >med
Book appointments with team members who are not set up to deliver those services>basic
Book appointments with resources that are not set up to deliver those services>basic
Services
Services>low
Memberships>low
Sales
Can check out sales>basic
Can edit prices at checkout>low
Can void invoices >low
Daily sales >basic
Appointments >basic
Can view all sales >basic
Gift Cards >basic
Memberships >basic
Product orders >basic
Can edit sale >low
Can add tips at checkout >basic
Can add cart discounts at checkout >basic
Can add discounts to cart items at checkout >basic
Can use cash as a payment method : all
Staff
Scheduled shifts >low
Closed dates >med
Team members >med
Permission levels >med
Gets notifications about tips >low
Appointment review reply >med
Run pay runs : owner only
Configure pin switching : owner only
Inventory
Products >low
Import products in bulk >med
Perform bulk operations >high
Data
Access reporting >med
Access reporting & insights : owner only
View all team members' data : owner only
Manage data connections : owner only
Setup
Account setup>med
Point of sale>med
Client settings>med
Online booking>med
Wallet and card processing>high
Marketing>med
Online store>med
Promotions
View deals>basic
Manage deals >med
Manage smart pricing >med
Gift Cards
View gift card list >basic
Manage gift cards >med
Consultation forms
Manage forms >low
View client responses >med
Complete forms>med
Notes
View notes >basic
Manage own notes >basic
Manage all notes >med
Timesheets
Manage own timesheets>med
Manage all timesheets>med
Manage timesheet settings>med
Rewards
Manage client rewards>med
Loyalty
View loyalty settings>basic
Manage loyalty settings>med
Manage clients' loyalty points and tiers>med
description:All logged in staff can access the calendar, and owner accounts have full system access.

5.3 Timesheets
fields:
-Proximity controls (bool.default:false,desc:Allow team members to only clock in within approximately 50m of the location.)
-Auto clock in (bool.default:false,desc:Automatically clock in at the beginning of scheduled shifts)
-Auto clock out (bool.default:false,desc:Automatically clock out at the end of scheduled shifts)
-Auto start and end scheduled breaks (bool.default:false,desc:Automatically record timesheet entries when scheduled breaks start and end)
description:
These settings can be customized individually per team member
5.4 Pay runs
fields:
-frequency:options(daily, weekly (default),every2week, every 4 weeks, monthly)
-restarts on (monday if weekly, 1st if monthly)
contidionts:
if frequency: weekly,every2week, every 4 weeks,: restart on days (mondy,tuesday...)
if frequency monthly: restart on 1...31
5.5 Commissions
fields:
Deduct discounts: bool:defaultTrue, desc: Deduct discounts applied to sale price of any product, service, membership and gift card, prior to calculating commission
Deduct taxes : bool:defaultTrue, desc: Deduct taxes from sale price prior to calculating commission
Deduct service cost:desc: bool:defaultFalse, Deduct service cost from sale price prior to calculating commission
Deduct product cost: bool:defaultFalse, Deduct product cost from sale price prior to calculating commission
Earn commission on services paid for with a membership: bool:defaultFalse, desc: Commission is earned on services paid for with a membership
Earn commissions on fully paid invoices: bool:defaultFalse,desc: Commission is only applied on invoices once they are marked as fully paid
5.6 PIN switching
fields:
-enable = default false
-Lock screen when inactive : default false
-Lock screen after checkout : default false
conditions:
if Lock screen when inactive:true, 10 sec, 30sec,1min(default),5min,10min,15min
#no need#
6.forms
6.1 form templates
##############
#cooming soon####
7.payments
7.1. payment policy
7.2 card termninals
##############
online presence:
8.marketplace profile
model: images
model: amenities: fields name,icon
fields: - images: foreign key image, max:10 - decription - enable
description:
image model File type .jpg, .png • minimum dimensions 916 x 500 pixels • max size 10 MB
9.reserve withgoogle
10.bookt with facebook and instagraö
11.link builder
marketing:
12.blast marketing 13. automations (trigger ve remindertype email & sms should support both can be enabled & disabled for each)
13.1 reminders
13.1.1 24 hours upcoming appointment reminder
13.1.2 1 hour upcoming appointment reminder
13.1.3 add new
13.2 appointment updates
13.2.1 New appointment
13.2.2 Rescheduled appointment
13.2.3 Canceled appointment
13.2.4 Didnotshowup
13.2.5 Thanks for visiting
13.3 waitlist updates
13.3.1 joined waitlist
13.3.2 Time slot avaible
13.4 increase bookings
13.4.1 reminder to rebook
13.4.2 Celerate birthdays
13.4.3.win back lapsed clients
13.4.4.reward loyal clients
13.5 Celebrate milestones
13.5.1 Welcome new clients
13.5.2 add new
13.6 Client loyalty
13.6.1 earned points summary
13.6.2 achieved loyality tier
13.6.3 earned rewards summary
13.6.4 referrer rewards earned
14.deals
type:1 protomotion
name
description
discount type (percentage-fixed), discount code
promotionstarts
promotion ends
bool:Enable promotion at Point of Sale
applyto(related):
-all services/select services (default: all)
-allproducts/select products (default: all)
-all memberships/select membership (default: all)
bool:Enable for gift cards (default: true)

    type:2 Flash sale
    name, description, discount type (percentage-fixed), discount code, promotionstarts, promotion ends, bool:Enable promotion at Point of Sale, applyto:
    -all services/select services
    -allproducts/select products
    -all memberships/select membership
    bool:Enable for gift cards

    type:1 Last-minute offer
    name, description, discount type (percentage-fixed), discount code, promotionstarts, promotion ends, bool:Enable promotion at Point of Sale, applyto:
    -all services/select services
    -allproducts/select products
    -all memberships/select membership
    bool:Enable for gift cards

15.smart pricing 16. sent messages
17.ratings and reviews
other:
18.add-ons
19.integrations
