# Picalor

## Multi-Channel Heat Balance Calorimetry on the Raspberry Pi
--> Incomplete - work-in-progress! <--

Thermal power (or heat flow) measurement of one segmented or multiple
individual liquid-cooled or liquid-heated systems under the assumption
that the enthalpy difference of the fluid entering and exiting each system
per unit of time is equal to the energy dissipated or released by the system.

Quasi-isothermal condition can be achieved by using a sufficiently high
flow rate. Accurate heat flow measurements under these conditions
require very sensitive and robust differential temperature sensing.

This is implemented by the Picalor hardware using platinum resistive
temperature sensors in a deflection-type bridge configuration connected
to a multi-channel, high-precision delta-sigma ADC system.

When performing the measurement with fluid temperatures set nearly at
environmental temperature level, convection and radiation heat loss
can be made negligible e.g. for power loss measurements in electronics.

For applications in chemistry, the multi-channel hardware can be useful
for Constant Flux Calorimetry or segmented Continuous Reaction Calorimters.

Supported hardware:

* Picalor OSHW Raspberry Pi add-on circuit board featuring:
    - 16-channel analog frontend for Pt 1000 sensors
    - 4x pulse-timing flow sensor inputs
    - 2x ADS1256 24-Bit 8-ch ADC
* Waveshare "High Precision AD/DA board"

## Hardware:
![Picalor PCB Photo](https://ul-gh.github.io/Picalor/picalor_hardware/picalor_pcb_photo.jpg)

* PCB Design Files: [picalor_hardware](picalor_hardware/)
* [Circuit Diagram (PDF)](https://ul-gh.github.io/Picalor/picalor_hardware/picalor_pcb.pdf)
* [Circuit BOM (HTML)](https://ul-gh.github.io/Picalor/picalor_hardware/ibom.html)

## Software Documentation (Generated):
* [Picalor Core (server component)](https://ul-gh.github.io/Picalor/picalor_core/html/namespaces.html)
* [Picalor App (browser client)](https://ul-gh.github.io/Picalor/picalor_app/html/files.html)