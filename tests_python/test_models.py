from __future__ import absolute_import
import datetime as dt
from decimal import Decimal
import pytest
from .util_tests import TestLogin
from evesrp import db
from evesrp.models import ActionType, Action, Request, Modifier,\
    AbsoluteModifier, RelativeModifier, StatusError, SRPPermissionError
from evesrp.auth import PermissionType
from evesrp.auth.models import Pilot, Division, Permission
from evesrp.util import utc


pytestmark = pytest.mark.usefixtures('request_context')


@pytest.fixture(params=ActionType.statuses)
def request_status(request, srp_request, other_user):
    # Skip if the status already matches
    if request.param == srp_request.status:
        return request.param
    # For paid status, we need to be approved first
    if request.param == ActionType.paid:
        Action(srp_request, other_user, type_=ActionType.approved)
    Action(srp_request, other_user, type_=request.param)
    db.session.commit()
    assert srp_request.status == request.param
    return request.param


@pytest.mark.parametrize('user_role', ['Normal'])
class TestModifiers(object):

    def test_add_modifier(self, srp_request, a_user, request_status):
        status_success = request_status == ActionType.evaluating
        permissions_success = 'Other' in a_user.name
        start_payout = srp_request.payout
        if status_success and permissions_success:
            AbsoluteModifier(srp_request, a_user, '', 10)
            db.session.commit()
            assert srp_request.payout == start_payout + 10
        # Status is checked before permissions
        elif status_success and not permissions_success:
            with pytest.raises(SRPPermissionError) as excinfo:
                AbsoluteModifier(srp_request, a_user, '', 10)
                db.session.commit()
        else:
            with pytest.raises(StatusError) as excinfo:
                AbsoluteModifier(srp_request, a_user, '', 10)
                db.session.commit()


    def test_void_modifier(self, srp_request, a_user, request_status):
        status_success = request_status == ActionType.evaluating
        permissions_success = 'Other' in a_user.name
        start_payout = srp_request.payout
        modifier = srp_request.modifiers[0]
        if status_success and permissions_success:
            modifier.void(a_user)
            db.session.commit()
            assert srp_request.payout == srp_request.base_payout
        # Request status is checked before permissions
        elif status_success and not permissions_success:
            with pytest.raises(SRPPermissionError) as excinfo:
                modifier.void(a_user)
                db.session.commit()
        else:
            with pytest.raises(StatusError) as excinfo:
                modifier.void(a_user)
                db.session.commit()

    @pytest.mark.xfail(reason="To be implemented")
    def test_evalutaion_order(self, user_role):
        pass




@pytest.mark.parametrize('user_role', ['Normal'])
class TestActionStatus(object):

    def test_default_status(self, srp_request):
        assert srp_request.status == ActionType.evaluating

    @pytest.fixture(params=ActionType.statuses)
    def next_status(self, request):
        return request.param

    # Also implicitly testing the setting of Request.status
    def test_state_machine(self, srp_request, other_user, request_status,
                           next_status):
        success = next_status in Request.state_rules[request_status]
        if success:
            Action(srp_request, other_user, type_=next_status)
            db.session.commit()
            assert srp_request.status == next_status
        else:
            with pytest.raises(StatusError) as excinfo:
                Action(srp_request, other_user, type_=next_status)
                db.session.commit()
            assert srp_request.status == request_status


@pytest.mark.parametrize('user_role', ['Normal'])
class TestDelete(object):

    def test_delete_action(self, srp_request, other_user):
        action = Action(srp_request, other_user, type_=ActionType.approved)
        db.session.commit()
        db.session.delete(action)
        db.session.commit()
        db.session.expire_all()
        assert srp_request is not None

    def test_delete_modifier(self, srp_request):
        modifier = srp_request.modifiers[0]
        db.session.delete(modifier)
        db.session.commit()
        db.session.expire_all()
        assert srp_request is not None

    def test_delete_request(self, srp_request, other_user):
        action = Action(srp_request, other_user, type_=ActionType.approved)
        modifier = srp_request.modifiers[0]
        db.session.commit()
        action_id = action.id
        modifier_id = modifier.id
        request_id = srp_request.id
        db.session.delete(srp_request)
        db.session.commit()
        db.session.expire_all()
        assert AbsoluteModifier.query.get(modifier_id) is None
        assert Action.query.get(action_id) is None
        assert Request.query.get(request_id) is None