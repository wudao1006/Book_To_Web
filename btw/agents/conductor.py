from btw.agents._placeholder import PlaceholderAgent


class ConductorAgent(PlaceholderAgent):
    name = "conductor"
    description = "Coordinates frontend transitions and global state."
    capability = "orchestration"
