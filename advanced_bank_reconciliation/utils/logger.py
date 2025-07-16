import logging

import frappe


def get_logger():
    logger = frappe.logger("bank_rec")
    logger.setLevel(logging.INFO)
    return logger
