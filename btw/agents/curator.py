from btw.agents._placeholder import PlaceholderAgent


class CuratorAgent(PlaceholderAgent):
    name = "curator"
    description = "Maintains reader-centric knowledge views and recommendations."
    capability = "curation"
