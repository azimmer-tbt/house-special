# input/

Drop raw vendor material here as you receive it: installers, DMGs, emailed license
files, the vendor's install notes. Everything in this folder except this README is
gitignored — vendor binaries never go into git.

Point the material scanner at it to match files against the catalogue:

    bin/analyze-materials.sh customer/acme/input --customer acme

Move each file to a durable store and list it in `output/files_to_copy.yaml` once a
recipe depends on it; `/tmp`-based vendor caches are cleared at reboot
(methodology lesson 24).
