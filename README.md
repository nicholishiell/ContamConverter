# ContamConverter

Convert a CONTAM FMU by unpacking it, injecting Linux runtime files, and repacking it.

## Install

```bash
sudo apt install pipx
pipx install .
pipx ensurepath
```

## Usage

```bash
ContamConverter \
  --contam_fmu /path/to/ContamFMU.fmu \
  --ctm_file /path/to/model.ctm \
  --wth_file /path/to/weather.wth
```

The converted FMU is written to `Converted-ContamFMU.fmu` in the current working directory.
