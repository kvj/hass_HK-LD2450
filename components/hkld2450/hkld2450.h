#pragma once

#include "esphome/core/component.h"
#include "esphome/components/uart/uart.h"
#include "esphome/components/api/api_server.h"
#include "esphome/core/log.h"
#include "esphome/core/hal.h"

#include <map>
#include <functional>

namespace esphome {
namespace hkld2450 {

#define INPUT_BUF_SIZE 160

typedef struct {
    uint8_t id;
    uint16_t x;
    uint16_t y;
    uint16_t w;
    uint16_t h;
    uint8_t  f;
} Zone;

class HKLD2450 : public esphome::PollingComponent, public esphome::uart::UARTDevice {
    private:
        uint8_t input_buf[INPUT_BUF_SIZE];
        int input_pos = 0;

        esphome::api::APIServer* api_server_ = 0;
        bool bluetooth_ = false;
        bool invert_x_ = false;

        int16_t x_[3] = {0, 0, 0};
        int16_t y_[3] = {0, 0, 0};
        int16_t  sp_[3] = {0, 0, 0};
        uint16_t res_[3] = {0, 0, 0};
        int8_t zone_[3] = {-1, -1, -1};

        std::vector<Zone> zones_ = {};

        uint16_t x__;
        uint16_t y__;
        uint16_t w__;
        uint16_t h__;
        uint16_t  a__;

    public:
        void setup() override;
        void loop() override;
        void update() override;

        void set_api_server(esphome::api::APIServer* api_server) { this->api_server_ = api_server; }
        void set_bluetooth(bool value) { this->bluetooth_ = value; }
        void set_invert_x(bool value) { this->invert_x_ = value; }

        void service_set_layout(int x, int y, int w, int h, int a);
        void service_add_zone(int x, int y, int w, int h, int f, int id);

    protected:
        void send_command(const uint8_t *command, size_t length);
        void handle_ack_data(const uint8_t *buffer, int len);
        void parse_frame(const uint8_t *b);

        void send_event_data();
        
};

}
}
