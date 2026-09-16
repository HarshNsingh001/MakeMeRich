import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';

import { colors } from '../theme/colors';
import { RootStackParamList, BottomTabParamList } from './types';

// Screens
import MarketPulseScreen from '../screens/MarketPulseScreen';
import OpportunitiesScreen from '../screens/OpportunitiesScreen';
import StockScreenerScreen from '../screens/StockScreenerScreen';
import WatchlistScreen from '../screens/WatchlistScreen';
import AlertsScreen from '../screens/AlertsScreen';
import StockDetailScreen from '../screens/StockDetailScreen';
import AgentDebateScreen from '../screens/AgentDebateScreen';

const Tab = createBottomTabNavigator<BottomTabParamList>();
const Stack = createNativeStackNavigator<RootStackParamList>();

const AppTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: colors.bgPrimary,
    card: colors.bgSecondary,
    text: colors.textPrimary,
    border: colors.border,
    primary: colors.accentBlue,
  },
};

function BottomTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.bgSecondary },
        headerTintColor: colors.textPrimary,
        tabBarStyle: { backgroundColor: colors.bgSecondary, borderTopColor: colors.border },
        tabBarActiveTintColor: colors.accentBlueBright,
        tabBarInactiveTintColor: colors.textSecondary,
      }}
    >
      <Tab.Screen name="MarketPulse" component={MarketPulseScreen} options={{ title: 'Pulse' }} />
      <Tab.Screen name="Opportunities" component={OpportunitiesScreen} />
      <Tab.Screen name="Screener" component={StockScreenerScreen} />
      <Tab.Screen name="Watchlist" component={WatchlistScreen} />
      <Tab.Screen name="Alerts" component={AlertsScreen} />
    </Tab.Navigator>
  );
}

export default function AppNavigator() {
  return (
    <NavigationContainer theme={AppTheme}>
      <Stack.Navigator
        screenOptions={{
          headerStyle: { backgroundColor: colors.bgSecondary },
          headerTintColor: colors.textPrimary,
        }}
      >
        <Stack.Screen 
          name="MainTabs" 
          component={BottomTabs} 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="StockDetail" 
          component={StockDetailScreen} 
          options={({ route }) => ({ title: route.params.symbol })} 
        />
        <Stack.Screen 
          name="AgentDebate" 
          component={AgentDebateScreen} 
          options={{ headerShown: false }} 
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
