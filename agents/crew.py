from crewai import Crew, Process


def make_crew(agents: list, tasks: list) -> Crew:
    """Create a sequential CrewAI crew from a list of agents and tasks."""
    return Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
