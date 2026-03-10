from btw.agents._placeholder import PlaceholderAgent


class TranslatorAgent(PlaceholderAgent):
    name = "translator"
    description = "Adapts output for language and accessibility targets."
    capability = "adaptation"
