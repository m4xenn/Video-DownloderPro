"""Compatibility exports; component and app update flows remain independent."""
from services.app_update_service import check_app_update
from services.component_updater import ComponentUpdater, component_status


def check_components():
    return component_status()['ready']
