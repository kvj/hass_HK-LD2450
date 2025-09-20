import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import uart, api

from esphome.const import (
    CONF_ID,
    CONF_UART_ID,
)

CODEOWNERS = ["@kvj"]
DEPENDENCIES = ["uart", "api"]
AUTO_LOAD = []

MULTI_CONF = False

CONF_API = "api_id"
CONF_BLUETOOTH = "bluetooth"
CONF_INVERT_X = "invert_x"

_ns = cg.esphome_ns.namespace("hkld2450")
_cls = _ns.class_("HKLD2450", cg.PollingComponent)

CONFIG_SCHEMA = (
    cv.Schema({
        cv.GenerateID(): cv.declare_id(_cls),
        cv.Required(CONF_UART_ID): cv.use_id(uart.UARTComponent),
        cv.Required(CONF_API): cv.use_id(api.APIServer),
        cv.Optional(CONF_BLUETOOTH, default=False): cv.boolean,
        cv.Optional(CONF_INVERT_X, default=False): cv.boolean,
    }).extend(cv.polling_component_schema("2s")).extend(uart.UART_DEVICE_SCHEMA)
)

async def to_code(config):
    cg.add_define("USE_API_HOMEASSISTANT_SERVICES")
    var = cg.new_Pvariable(config[CONF_ID])
    cg.add(var.set_api_server(await cg.get_variable(config[CONF_API])))
    cg.add(var.set_bluetooth(config[CONF_BLUETOOTH]))
    cg.add(var.set_invert_x(config[CONF_INVERT_X]))
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
