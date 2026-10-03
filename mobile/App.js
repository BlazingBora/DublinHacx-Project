import { StatusBar } from "expo-status-bar";
import { useState } from "react";
import HomeScreen from "./screens/HomeScreen";
import RecipeScreen from "./screens/RecipeScreen";
import ResultsScreen from "./screens/ResultsScreen";

export default function App() {
  const [screen, setScreen] = useState("home");
  const [results, setResults] = useState(null); // { mode, items, interactions, names }
  const [recipe, setRecipe] = useState(null);
  const [knownMedications, setKnownMedications] = useState([]);
  const [knownGroceries, setKnownGroceries] = useState([]);
  const [homeError, setHomeError] = useState(null);

  const handleResults = (data) => {
    setHomeError(null);

    if (data.mode === "grocery") {
      setKnownGroceries(data.names || []);
    } else {
      setKnownMedications(data.names || []);
    }

    setResults(data);
    setScreen("results");
  };

  const goHome = () => {
    setResults(null);
    setRecipe(null);
    setScreen("home");
  };

  return (
    <>
      {screen === "home" && (
        <HomeScreen
          knownMedications={knownMedications}
          knownGroceries={knownGroceries}
          onResults={handleResults}
          error={homeError}
        />
      )}

      {screen === "results" && results && (
        <ResultsScreen
          mode={results.mode}
          items={results.items}
          interactions={results.interactions}
          onBack={goHome}
          onRecipe={(recipeData) => {
            setRecipe(recipeData);
            setScreen("recipe");
          }}
        />
      )}

      {screen === "recipe" && recipe && (
        <RecipeScreen recipe={recipe} onBack={goHome} />
      )}

      <StatusBar style="light" />
    </>
  );
}
