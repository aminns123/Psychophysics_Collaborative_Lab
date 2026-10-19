"""Live explanatory domains, backed by the same specification/preflight validators."""
from .models import SetupRequest
from .preflight import validate_setup


def experiment_constraints(spec,profile,raw):
    reports={}; parsed={}; errors=[]
    for field in spec.fields:
        domain='Allowed choices: '+', '.join(map(str,field.choices)) if field.kind=='choice' else (
            ('Whole number' if field.kind=='int' else 'Finite number')+f"; range {field.minimum if field.minimum is not None else 'no declared lower bound'} to {field.maximum if field.maximum is not None else 'no declared upper bound'}" if field.kind in ('int','float') else 'Text; '+field.help_text)
        report={'domain':domain,'error':'','classification':'fixed / experiment specification'}
        try: parsed[field.key]=field.coerce(raw.get(field.key))
        except (ValueError,TypeError) as exc: report['error']=str(exc)
        reports[field.key]=report
    pass  # Retired protocol branch removed.
    if len(parsed)==len(spec.fields):
        try: validate_setup(SetupRequest('input_preview','new',spec.id,profile.id,parsed),spec,profile,mode='configuration')
        except (ValueError,TypeError) as exc:
            errors=str(exc).splitlines()
            for message in errors:
                matching=[f.key for f in spec.fields if f.key.lower() in message.lower() or f.label.split(' (')[0].lower() in message.lower()]
                pass  # Retired protocol branch removed.
                for key in matching: reports[key]['error']=message
    return reports,errors
