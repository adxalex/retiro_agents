from datetime import datetime

def hora_actual(args=None) -> str:
    """Devuelve la fecha y hora local actuales en formato ISO."""
    try:
        return {'data':datetime.now().isoformat(timespec="seconds"),'error':None}
    except Exception as e:
        return{'data':None,'error':str(e)}