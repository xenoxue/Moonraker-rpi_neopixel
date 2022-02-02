#!/bin/bash
MOONRAKER_PATH="${HOME}/moonraker"
MOONRAKER-ENV_PATH="${HOME}/moonraker-env"
KLIPPER_CONFIG_PATH="${HOME}/klipper_config"

# Step 1:  Verify Moonraker has been installed
check_moonraker()
{
    if [ "$(sudo systemctl list-units --full -all -t service --no-legend | grep -F "moonraker.service")" ]; then
        echo "Moonraker service found!"
    else
        echo "Moonraker service not found, please install Moonraker first"
        exit -1
    fi
}

# Step 2: link extension to Moonraker
link_extension()
{
    echo "Linking extension to Moonraker..."
    ln -sf "${SRCDIR}/rpi_neopixel.py" "${MOONRAKER_PATH}/moonraker/components/rpi_neopixel.py"
}

# Step 3: Add updater
# webcamd to moonraker.conf
add_updater()
{
    echo -e "Adding update manager to moonraker.conf"

    update_section=$(grep -c '\[update_manager rpi_neopixel\]' \
    ${HOME}/klipper_config/moonraker.conf || true)
    if [ "${update_section}" -eq 0 ]; then
    echo -e "\n" >> ${HOME}/klipper_config/moonraker.conf
    while read -r line; do
        echo -e "${line}" >> ${HOME}/klipper_config/moonraker.conf
    done < "$PWD/file_templates/moonraker_update.txt"
    echo -e "\n" >> ${HOME}/klipper_config/moonraker.conf
    else
    echo -e "[update_manager rpi_neopixel] already exist in moonraker.conf [SKIPPED]"
    fi
}


# Step 4: Install NeoPixel Library
install_neopixel()
{
    echo "Installing adafruit-circuitpython-neopixel..."
    sudo ${MOONRAKER-ENV_PATH}/bin/pip install rpi_ws281x adafruit-circuitpython-neopixel
    echo "Installing adafruit-blinka..."
    sudo ${MOONRAKER-ENV_PATH}/bin/pip install --force-reinstall adafruit-blinka
}

# Step 5: ADD Sudoer nopasswd permission file to give more access for pi user.
add_permission()
{
    echo "Adding SUDO NOPASSWD permission for Moonraker..."
    if sudo grep -E "^pi*" /etc/sudoers; then
        sudo sed -i "s|^pi.*$|pi    ALL=(ALL)   NOPASSWD:SETENV: /home/pi/moonraker-env/bin/python|g" /etc/sudoers
    else
        sudo echo "pi   ALL=(ALL)   NOPASSWD:SETENV: /home/pi/moonraker-env/bin/python" >> /etc/sudoers
    fi
}

# Step 6: Edit Moonraker.service, need to run as SUDO. as the Root access is required to access the RPi peripherals.
edit_service()
{
    echo "Adding SUDO command to run Moonraker Service..."
    if sudo grep -E "^ExecStart=sudo*" /etc/systemd/system/moonraker.service; then
        echo "Moonraker Service already running with SUDO..."
    else
        sudo sed -i "s|^ExecStart.*$|ExecStart=sudo -E /home/pi/moonraker-env/bin/python /home/pi/moonraker/moonraker/moonraker.py -c /home/pi/klipper_config/moonraker.conf -l /home/pi/klipper_logs/moonraker.log|g" /etc/systemd/system/moonraker.service
        echo "Reloading Moonraker Service file..."
        systemctl daemon-reload
    fi
}

# Step 7: restarting Moonraker
restart_moonraker()
{
    echo "Restarting Moonraker..."
    sudo systemctl restart Moonraker
}

# Helper functions
verify_ready()
{
    if [ "$EUID" -eq 0 ]; then
        echo "This script must not run as root"
        exit -1
    fi
}

# Force script to exit if an error occurs
set -e

# Find SRCDIR from the pathname of this script
SRCDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/src/ && pwd )"

# Parse command line arguments
while getopts "k:" arg; do
    case $arg in
        k) MOONRAKER_PATH=$OPTARG;;
    esac
done

# Run steps
verify_ready
link_extension
add_updater
install_neopixel
replace_path
edit_service
restart_moonraker