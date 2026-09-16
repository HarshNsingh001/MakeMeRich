import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';

export default function WatchlistScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.header}>My Watchlists</Text>
      
      <View style={styles.card}>
        <Text style={styles.listName}>Core Portfolio</Text>
        <Text style={styles.stockCount}>5 stocks</Text>
      </View>
      
      <View style={styles.card}>
        <Text style={styles.listName}>Tech Breakouts</Text>
        <Text style={styles.stockCount}>12 stocks</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bgPrimary, padding: 20 },
  header: { fontSize: 24, fontWeight: 'bold', color: colors.textPrimary, marginBottom: 20 },
  card: { backgroundColor: colors.bgCard, padding: 20, borderRadius: 12, borderWidth: 1, borderColor: colors.borderLight, marginBottom: 12 },
  listName: { color: colors.textPrimary, fontWeight: 'bold', fontSize: 18, marginBottom: 4 },
  stockCount: { color: colors.textSecondary, fontSize: 14 }
});
