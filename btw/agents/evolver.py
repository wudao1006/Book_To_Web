from btw.agents._placeholder import PlaceholderAgent


class EvolverAgent(PlaceholderAgent):
    name = "evolver"
    description = "Learns from executions to improve prompts and policies."
    capability = "optimization"
