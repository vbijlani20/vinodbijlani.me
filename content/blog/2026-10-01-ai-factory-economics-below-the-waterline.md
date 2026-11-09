---
title: AI factory economics gets interesting below the waterline
date: 2026-10-01
summary: A GPU is a capital decision. Power, cooling, networking, utilisation and staging compound over the life of the AI factory.
image: media/economics-of-ai-factory.gif
image_alt: "The economics of an AI factory: the costs below the waterline"
tags: [AI factories, AI economics, Data centres]
infographic:
  type: stats
  title: Below the waterline
  items:
    - {value: "~$7M", label: "a year saved by improving PUE from 1.2 to 1.1 on a 100 MW IT load (at $0.08/kWh)"}
    - {value: "2×", label: "the cost of useful compute at 40% versus 80% productive utilisation"}
    - {value: "100 kW+", label: "rack architectures change facility design, power and cooling at once"}
  foot: "Move from $/GPU-hour → $/token → $/useful token."
---

AI data centre economics gets interesting below the waterline. Not because the costs are invisible, but because they scale differently.

A GPU is largely a capital-cost decision. Several other variables compound over the operating life of an AI factory.

**Power compounds with PUE and utilisation.** A 100 MW IT load at a PUE of 1.2 needs roughly 120 MW at the facility. Improve PUE to 1.1 and you save around 10 MW, continuously. At $0.08 per kWh, that is around $7 million a year from one decimal point.

**Cooling economics change with rack density.** The question is shifting from "how many racks can I fit?" to "how many kW can I reliably cool per rack?" Moving toward 100 kW+ racks changes facility design, power distribution and cooling all at once.

**Network design shows up in GPU economics.** An expensive accelerator waiting on data is still consuming capital. Fabric topology, bandwidth and oversubscription show up indirectly in GPU utilisation, and ultimately in cost per token.

**Utilisation changes the denominator.** A $/GPU-hour number can look attractive while the cluster underneath is poorly utilised. At 40% versus 80% productive utilisation, useful compute costs twice as much.

**Staging creates a timing problem.** Power may arrive before GPUs. GPUs may arrive before cooling. Buildings may be ready before the grid connection. Every mismatch is capital that has been spent, often debt-funded and accruing interest, without producing a single token.

And then there's the one I think deserves much more attention: **stranded capacity**. AI hardware generations are moving faster than data centre infrastructure. You can replace GPUs in a few years. Replacing the power envelope, cooling architecture or network topology underneath them is much harder.

So AI factory economics needs to move beyond $/GPU-hour to $/token to **$/useful token**. The last metric forces us to account for the whole factory: compute, power, cooling, network, utilisation and capital. That's where AI infrastructure design becomes an economics problem.

What would you put below the waterline?
