# # subscriptions.py
#
# from datetime import datetime, timedelta
# from src.db.database import Database
# from src.api_manager.vpn_panel import VPNPanelAPI
#
# db = Database()
# vpn_api = VPNPanelAPI()
#
# async def add_trial_subscription(user_id, username, inbound_id):
#     start_date = datetime.now()
#     end_date = start_date + timedelta(days=3)
#     await db.add_subscription(user_id, username, "3 дня пробного доступа", start_date, end_date)
#     vpn_api.add_client(3, username, user_id)
#
# async def add_paid_subscription(user_id, username, subscription_type, days, inbound_id):
#     start_date = datetime.now()
#     end_date = start_date + timedelta(days=days)
#     await db.add_subscription(user_id, username, subscription_type, start_date, end_date)
#     vpn_api.add_client(days, username, user_id)
